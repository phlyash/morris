from enum import IntEnum

MAGIC_BYTE = 0x4D
VERSION = 1


class DataType(IntEnum):
    UINT8 = 0
    UINT16 = 1
    UINT32 = 2
    UINT64 = 3
    FLOAT = 4
    DOUBLE = 5

    def to_struct_fmt(self) -> str:
        mapping = {
            0: 'B', 1: 'H', 2: 'I', 3: 'Q', 4: 'f', 5: 'd'
        }
        return mapping[self.value]

    def get_size(self) -> int:
        mapping = {
            0: 1, 1: 2, 2: 4, 3: 8, 4: 4, 5: 8
        }
        return mapping[self.value]


class BlockType(IntEnum):
    FRAMES = 1
    STATS = 2
    METADATA = 3
