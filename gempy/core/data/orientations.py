﻿from dataclasses import dataclass
from typing import Optional

import numpy as np

from gempy.optional_dependencies import require_pandas

DEFAULT_NUGGET = 0.01

# ? Maybe we should merge this with the SurfacePoints class from gempy_engine


@dataclass
class OrientationsTable:
    data: np.ndarray
    name_id_map: Optional[dict[str, int]] = None  # ? Do I need this here or this should be a field of StructuralFrame?

    dt = np.dtype([('X', 'f8'), ('Y', 'f8'), ('Z', 'f8'), ('G_x', 'f8'), ('G_y', 'f8'), ('G_z', 'f8'), ('id', 'i4'), ('nugget', 'f8')])

    def __str__(self):
        return "\n" + np.array2string(self.data, precision=2, separator=',', suppress_small=True)

    def __repr__(self):
        return self.__str__()

    def __len__(self):
        return len(self.data)

    @classmethod
    def from_arrays(cls, x: np.ndarray, y: np.ndarray, z: np.ndarray,
                    G_x: np.ndarray, G_y: np.ndarray, G_z: np.ndarray,
                    names: np.ndarray, nugget: Optional[np.ndarray] = None) -> 'OrientationsTable':

        if nugget is None:
            nugget = np.zeros_like(x) + DEFAULT_NUGGET

        data = np.zeros(len(x), dtype=OrientationsTable.dt)

        name_id_map = {name: i for i, name in enumerate(np.unique(names))}
        ids = np.array([name_id_map[name] for name in names])

        data['X'], data['Y'], data['Z'], data['G_x'], data['G_y'], data['G_z'], data['id'], data['nugget'] = x, y, z, G_x, G_y, G_z, ids, nugget
        return cls(data, name_id_map)

    @property
    def xyz(self) -> np.ndarray:
        return np.array([self.data['X'], self.data['Y'], self.data['Z']]).T
    
    @property
    def grads(self) -> np.ndarray:
        return np.array([self.data['G_x'], self.data['G_y'], self.data['G_z']]).T

    @property
    def ids(self) -> np.ndarray:
        return self.data['id']
    
    def get_orientations_by_name(self, name: str) -> 'OrientationsTable':
        return self.get_orientations_by_id(self.name_id_map[name])

    def get_orientations_by_id(self, id: int) -> 'OrientationsTable':
        return OrientationsTable(self.data[self.data['id'] == id], self.name_id_map)
    
    def get_orientations_by_id_groups(self) -> list['OrientationsTable']:
        ids = np.unique(self.data['id'])
        return [self.get_orientations_by_id(id) for id in ids]

    @classmethod
    def fill_missing_orientations_groups(cls, orientations_groups: list['OrientationsTable'],
                                         surface_points_groups: list['SurfacePointsTable']) -> list['OrientationsTable']:
        # region Deal with elements without orientations
        if len(surface_points_groups) > len(orientations_groups):
            # Check the ids of the surface points and find the missing ones
            surface_points_ids = [surface_points_group.id for surface_points_group in surface_points_groups]
            orientations_ids = [orientations_group.id for orientations_group in orientations_groups]

            missing_ids = list(set(surface_points_ids) - set(orientations_ids))

            empty_orientations = [cls(data=np.zeros(0, dtype=cls.dt)) for id in missing_ids] # Create empty orientations

            for empty_orientation, id in zip(empty_orientations, missing_ids): # Insert the empty orientations in the right position
                orientations_groups.insert(id, empty_orientation)
        # endregion

        return orientations_groups
    
    @property
    def id(self) -> int:
        # Check id is the same in the whole column and return it or throw an error
        ids = np.unique(self.data['id'])
        if len(ids) > 1:
            raise ValueError(f"OrientationsTable contains more than one id: {ids}")
        if len(ids) == 0:
            raise ValueError(f"OrientationsTable contains no ids")
        return ids[0]
    
    @property
    def df(self) -> 'pd.DataFrame':
        pd = require_pandas()
        return pd.DataFrame(self.data)

