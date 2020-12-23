import sys
import os
from math import floor
import re
import zlib
import copy
from nbt import nbt, world
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

    # Search and substitute action starts here
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

