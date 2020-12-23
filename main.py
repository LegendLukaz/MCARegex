# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import sys
import os
from math import floor
import re
import zlib
import copy
from nbt import nbt, world

regcoordf = re.compile(r"r\.([-0-9]+)\.([-0-9]+).+")

SECTOR_SIZE = 4096 # 4KiB


class chunk(object):
    def __init__(self, offset, nsec, rf):
        if offset is not None and nsec is not None and rf is not None:
            # Save location for next read
            currloc = rf.tell()
            self.nsec = nsec
            self.offset = offset * SECTOR_SIZE

            self.readts(rf)

            self.readchunk(rf)

            # Return to original location
            rf.seek(currloc)

    def readts(self, rf):
        # Read timestamp, 4 bytes long
        rf.seek(4096, 1)
        self.ts = int.from_bytes(rf.read(4), "big")

    def readchunk(self, rf):
        # Read in chunk
        rf.seek(self.offset)
        self.chunklen = int.from_bytes(rf.read(4), "big")
        self.comptype = int.from_bytes(rf.read(1), "big")

        if self.comptype != 2:
            print("Compression type not supported.")
            raise NotImplementedError

        self.nbtData = zlib.decompress(rf.read(self.chunklen - 1))

    @classmethod
    def empty(cls):
        """Create empty chunk (does nothing)"""
        return cls(None, None, None)


def readregion(rootfn: str, fn: str):
    fullfname = rootfn + "\\" + fn
    with open(fullfname, "rb") as rf:
        region = {}
        bc = list(map(int, regcoordf.fullmatch(filename).group(1, 2)))
        region["base_coord"] = (bc[0] << 5, bc[1] << 5)

        region["chunks"] = [[chunk.empty()] * 32] * 32

        # 1024 chunks in one region file
        for i in range(1024):
            locOffset = int.from_bytes(rf.read(3), 'big')
            secCount = int.from_bytes(rf.read(1), 'big')

            if (locOffset != 0) and (secCount != 0):
                region["chunks"][i // 32][i % 32] = chunk(locOffset, secCount, rf)

        return region


# Convert chunk coord to region coord
def chunk2reg(x, z):
    rx = floor(x / 32.0)
    rz = floor(z / 32.0)

    return rx, rz

from nbt.nbt import NBTFile, TAG_Long, TAG_Double, TAG_Int, TAG_String, TAG_List, TAG_Compound

def unpack_nbt(tag):
    """
    Unpack an NBT tag into a native Python data structure.
    """

    if isinstance(tag, TAG_List):
        return [unpack_nbt(i) for i in tag.tags]
    elif isinstance(tag, TAG_Compound):
        return dict((i.name, unpack_nbt(i)) for i in tag.tags)
    else:
        return tag.value

def pack_nbt(s):
    """
    Pack a native Python data structure into an NBT tag. Only the following
    structures and types are supported:
     * int
     * float
     * str
     * unicode
     * dict
    Additionally, arbitrary iterables are supported.
    Packing is not lossless. In order to avoid data loss, TAG_Long and
    TAG_Double are preferred over the less precise numerical formats.
    Lists and tuples may become dicts on unpacking if they were not homogenous
    during packing, as a side-effect of NBT's format. Nothing can be done
    about this.
    Only strings are supported as keys for dicts and other mapping types. If
    your keys are not strings, they will be coerced. (Resistance is futile.)
    """

    if isinstance(s, int):
        return TAG_Long(s)
    elif isinstance(s, float):
        return TAG_Double(s)
    elif isinstance(s, str):
        return TAG_String(s)
    elif isinstance(s, dict):
        tag = TAG_Compound()
        for k, v in s.items():
            v = pack_nbt(v)
            v.name = str(k)
            tag.tags.append(v)
        return tag
    elif hasattr(s, "__iter__"):
        # We arrive at a slight quandry. NBT lists must be homogenous, unlike
        # Python lists. NBT compounds work, but require unique names for every
        # entry. On the plus side, this technique should work for arbitrary
        # iterables as well.
        tags = [pack_nbt(i) for i in s]
        if tags:
            t = type(tags[0])
            # If we're homogenous...
            if all(t == type(i) for i in tags):
                tag = TAG_List(type=t)
                tag.tags = tags
            else:
                tag = TAG_Compound()
                for i, item in enumerate(tags):
                    item.name = str(i)
                tag.tags = tags
        else:
            tag = TAG_List(type=None)
        return tag
    else:
        raise ValueError("Couldn't serialise type %s!" % type(s))


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    worldPath = "./data"
    tagType = "TileEntities"
    id = "minecraft:command_block"
    key = "Command" # Optional
    searchStr = r"(?<=@[ap]\[)([0-9,]+)(?=\])"

    def subfunc(s):
        s = str(s.group(1))
        s = s.split(",")
        s.reverse()

        x = s.pop()
        y = s.pop()
        z = s.pop()
        result = f"x={x},y={y},z={z}"
        if s:
            dist = s.pop()
            result = result + f",distance={dist}"

        return result

    # if len(sys.argv) > 1:
    #     worldPath = sys.argv[1]

    sp = re.compile(searchStr)

    worldObj = world.WorldFolder(worldPath)
    for reg in worldObj.iter_regions():
        for chunk in reg.iter_chunks():
            subtag = chunk["Level"][tagType]

            dirtybit = False
            for entry in subtag:
                if entry["id"].value == id:
                    print(entry.pretty_tree())
                    if key:
                        entry[key].value, n = sp.subn(subfunc, entry[key].value)
                        dirtybit = (n > 0 or dirtybit)
                    else:
                        for k, v in entry.items():
                            entry[k].value, n = sp.subn(subfunc, v)
                            dirtybit = (n > 0 or dirtybit)

                    print(entry.pretty_tree())

            # TODO: queue up chunks to be written into region file directly

            if dirtybit:
                reg.write_chunk(chunk.loc.x, chunk.loc.z, chunk)





    # for root, dirs, files in os.walk(worldPath):
    #     regions = [None] * len(files)
    #     for i, filename in enumerate(files):
    #         # regions[i] = readregion(worldPath, filename)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
