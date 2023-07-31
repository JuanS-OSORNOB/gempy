﻿from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from gempy_engine.core.data.input_data_descriptor import InputDataDescriptor
from gempy_engine.core.data.stack_relation_type import StackRelationType
from .orientations import OrientationsTable
from .structural_element import StructuralElement
from .structural_group import StructuralGroup, FaultsRelationSpecialCase
from .surface_points import SurfacePointsTable
from ..color_generator import ColorsGenerator


@dataclass
class StructuralFrame:
    structural_groups: list[StructuralGroup]  # ? should this be lazy?
    color_gen: ColorsGenerator

    # fault_relations: Optional[np.ndarray] = None

    # ? Should I create some sort of structural options class? For example, the masking descriptor and faults relations pointer
    is_dirty: bool = True  # This changes when the structural frame is modified

    def __init__(self, structural_groups: list[StructuralGroup], color_gen: ColorsGenerator):
        self.structural_groups = structural_groups  # ? This maybe could be optional
        self.color_gen = color_gen

    def __repr__(self):
        structural_groups_repr = ',\n'.join([repr(g) for g in self.structural_groups])
        fault_relations_str = np.array2string(self.fault_relations) if self.fault_relations is not None else 'None'
        return (f"StructuralFrame(\n"
                f"\tstructural_groups=[\n{structural_groups_repr}\n],\n"
                f"\tfault_relations={fault_relations_str},\n"
                )

    def _repr_html_(self):
        structural_groups_html = '<br>'.join([g._repr_html_() for g in self.structural_groups])
        fault_relations_str = np.array2string(self.fault_relations) if self.fault_relations is not None else 'None'
        html = f"""
    <table >
      <tr><td>Structural Groups:</td><td>{structural_groups_html}</td></tr>
      <tr><td>Fault Relations:</td><td>{fault_relations_str}</td></tr>
    </table>
        """
        return html

    @property
    def structural_elements(self) -> list[StructuralElement]:
        elements = []
        for group in self.structural_groups:
            elements.extend(group.elements)
        elements.append(self._basement_element)
        return elements

    @property
    def _basement_element(self) -> StructuralElement:
        basement = StructuralElement(
            name="basement",
            surface_points=SurfacePointsTable(data=np.zeros(0, dtype=SurfacePointsTable.dt)),
            orientations=OrientationsTable(data=np.zeros(0, dtype=OrientationsTable.dt)),
            color=self.color_gen.up_next(),
        )

        return basement

    @property
    def fault_relations(self):
        # Initialize an empty boolean array with dimensions len(structural_groups) x len(structural_groups)
        fault_relations = np.zeros((len(self.structural_groups), len(self.structural_groups)), dtype=bool)

        # We assume that the list is ordered from older to younger
        # Iterate over the list of structural_groups
        for i, group in enumerate(self.structural_groups):
            match (group.structural_relation, group.fault_relations):
                case (StackRelationType.FAULT, FaultsRelationSpecialCase.OFFSET_ALL):
                    # It affects all younger groups
                    fault_relations[i, i + 1:] = True
                case (StackRelationType.FAULT, FaultsRelationSpecialCase.OFFSET_NONE):
                    # It affects no groups
                    pass
                case (StackRelationType.FAULT, list(fault_groups)) if fault_groups:
                    # It affects only the specified groups
                    for fault_group in fault_groups:
                        j = self.structural_groups.index(fault_group)
                        if j <= i:  # Only consider groups that are 
                            raise ValueError(f"Fault {group.name} cannot affect older fault {fault_group.name}")
                case (StackRelationType.FAULT, _):
                    raise ValueError(f"Fault {group.name} has an invalid fault relation")
                case _:
                    pass  # If not a fault or fault relation is not specified, do nothing
        return fault_relations

    @fault_relations.setter
    def fault_relations(self, matrix: np.ndarray):
        assert matrix.shape == (len(self.structural_groups), len(self.structural_groups))

        # Iterate over each StructuralGroup
        for i, group in enumerate(self.structural_groups):
                
            affected_groups = matrix[i, :]  # * If the group is a fault
            # If all younger groups are affected
            all_younger_groups_affected = np.all(affected_groups[i + 1:])
            any_younger_groups_affected = np.any(affected_groups[i + 1:])
            
            if all_younger_groups_affected:
                group.fault_relations = FaultsRelationSpecialCase.OFFSET_ALL
                group.structural_relation = StackRelationType.FAULT
            elif not any_younger_groups_affected:
                group.fault_relations = FaultsRelationSpecialCase.OFFSET_NONE
            else:  # * A specific set of groups are affected
                group.fault_relations = [g for j, g in enumerate(self.structural_groups) if affected_groups[j]]
                group.structural_relation = StackRelationType.FAULT

    @property
    def input_data_descriptor(self):
        # TODO: This should have the exact same dirty logic as interpolation_input

        self._validate_faults_relations()
        return InputDataDescriptor.from_structural_frame(
            structural_frame=self,
            making_descriptor=self.groups_structural_relation,
            faults_relations=self.fault_relations
        )

    @property
    def number_of_points_per_element(self) -> np.ndarray:
        return np.array([element.number_of_points for element in self.structural_elements])

    @property
    def number_of_points_per_group(self) -> np.ndarray:
        return np.array([group.number_of_points for group in self.structural_groups])

    @property
    def number_of_orientations_per_group(self) -> np.ndarray:
        return np.array([group.number_of_orientations for group in self.structural_groups])

    @property
    def number_of_elements_per_group(self) -> np.ndarray:
        return np.array([group.number_of_elements for group in self.structural_groups])

    @property
    def surfaces(self) -> list[StructuralElement]:
        return self.structural_elements

    @property
    def number_of_elements(self) -> int:
        return len(self.structural_elements)

    @property
    def groups_structural_relation(self) -> list[StackRelationType]:
        groups_ = [group.structural_relation for group in self.structural_groups]
        groups_[-1] = False
        return groups_

    @property
    def elements_names(self) -> list[str]:
        return [element.name for element in self.structural_elements]

    @property
    def elements_ids(self) -> np.ndarray:
        """Return id given by the order of the structural elements"""
        return np.arange(len(self.structural_elements)) + 1

    @property
    def surface_points(self) -> SurfacePointsTable:
        all_data: np.ndarray = np.concatenate([element.surface_points.data for element in self.structural_elements])
        return SurfacePointsTable(data=all_data, name_id_map=self.element_name_id_map)

    @property
    def element_id_name_map(self) -> dict[int, str]:
        return {i: element.name for i, element in enumerate(self.structural_elements)}

    @property
    def element_name_id_map(self) -> dict[str, int]:
        return {element.name: i for i, element in enumerate(self.structural_elements)}

    @property
    def elements_colors(self) -> list[str]:
        # reversed
        return [element.color for element in self.structural_elements][::-1]

    @property
    def elements_colors_volumes(self) -> list[str]:
        return self.elements_colors

    @property
    def elements_colors_contacts(self) -> list[str]:
        elements_ = [element.color for element in self.structural_elements]
        return elements_

    @property
    def surface_points_colors(self) -> list[str]:
        """Using the id record of surface_points map the elements colors to each point"""
        surface_points_colors = [element.color for element in self.structural_elements for _ in range(element.number_of_points)]
        return surface_points_colors

    @property
    def orientations_colors(self) -> list[str]:
        """Using the id record of orientations map the elements colors to each point"""
        orientations_colors = [element.color for element in self.structural_elements for _ in range(element.number_of_orientations)]
        return orientations_colors

    @property
    def orientations(self) -> OrientationsTable:
        all_data: np.ndarray = np.concatenate([element.orientations.data for element in self.structural_elements])
        return OrientationsTable(data=all_data)

    @property
    def groups_to_mapper(self) -> dict[str, list[str]]:
        result_dict = {}
        for group in self.structural_groups:
            element_names = [element.name for element in group.elements]
            result_dict[group.name] = element_names
        return result_dict

    # region Depends on Pandas
    @property
    def surfaces_df(self) -> 'pd.DataFrame':
        # TODO: Loop every structural element. Each element should be a row in the dataframe
        # TODO: The columns have to be ['element, 'group', 'color']

        raise NotImplementedError

    # endregion

    def _validate_faults_relations(self):
        """Check that if there are any StackRelationType.FAULT in the structural groups the fault relation matrix is
        given and shape is the right one, i.e. a square matrix of size equals to len(groups)"""

        if any([group.structural_relation == StackRelationType.FAULT for group in self.structural_groups]):
            if self.fault_relations is None:
                raise ValueError("The fault relations matrix is not given")
            if self.fault_relations.shape != (len(self.structural_groups), len(self.structural_groups)):
                raise ValueError("The fault relations matrix is not the right shape")
