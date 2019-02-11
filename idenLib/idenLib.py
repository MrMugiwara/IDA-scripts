# -------------------------------------------------------------------------------
#
# Copyright (c) 2018, Lasha Khasaia @_qaz_qaz
# Licensed under the GNU GPL v3.
#
# -------------------------------------------------------------------------------


from __future__ import print_function
import ida_name
import ida_bytes
import ida_funcs
import idaapi
import ida_idaapi
import ida_diskio
import idautils
import ida_name
import os
import zstd
from capstone import *

MIN_FUNC_SIZE = 0x20
MAX_FUNC_SIZE = 0x100
PLUGIN_NAME = "idenLib"
PLUGIN_VERSION = "v0.3"

# __EA64__ is set if IDA is running in 64-bit mode
__EA64__ = ida_idaapi.BADADDR == 0xFFFFFFFFFFFFFFFFL

if __EA64__ :
    CAPSTONE_MODE = CS_MODE_64
    SIG_EXT = ".sig64"
else:
    CAPSTONE_MODE = CS_MODE_32
    SIG_EXT = ".sig"

def get_names():
    for ea, name in idautils.Names():
        yield name

def files(path):  
    for file in os.listdir(path):
        if os.path.isfile(os.path.join(path, file)):
            yield path + "\\" + file

# return (start_ea, size)
def get_func_ranges():
    funcs_addr = []
    start = 0
    next_func =  ida_funcs.get_next_func(start)
    while next_func:
        size = next_func.size()
        if (size) < MIN_FUNC_SIZE:
           next_func = ida_funcs.get_next_func(next_func.start_ea)
           continue
        elif size > MAX_FUNC_SIZE:
            size = MAX_FUNC_SIZE
        yield (next_func.start_ea, size)
        funcs_addr.append(next_func.start_ea - start)
        next_func = ida_funcs.get_next_func(next_func.start_ea)

def getOpcodes(addr, size):
    md = Cs(CS_ARCH_X86, CAPSTONE_MODE)
    md.detail = True
    instr_bytes = ida_bytes.get_bytes(addr, size)
    opcodes_buf = b''
    for i in md.disasm(instr_bytes, size):
        # get last opcode
        if (i.opcode[3] != 0):
            opcodes_buf += "%02x" % (i.opcode[3])
        elif (i.opcode[2] != 0):
            opcodes_buf += "%02x" % (i.opcode[2])
        elif(i.opcode[1] != 0):
            opcodes_buf += "%02x" % (i.opcode[1])
        else:
            opcodes_buf += "%02x" % (i.opcode[0])
    return opcodes_buf

def idenLib():
    # function sigs from the current binary
    func_bytes_addr = {}
    for addr, size in get_func_ranges():
        f_bytes = getOpcodes(addr, size)
        func_bytes_addr[f_bytes] = addr
        
    # load sigs
    func_sigs = {}
    ida_dir = ida_diskio.idadir("")
    symEx_dir = ida_dir + os.sep + "SymEx"
    if not os.path.isdir(symEx_dir):
        printf("[idenLib - FAILED] There is no {} directory".format(symEx_dir))
    else:
        for file in files(symEx_dir):
            if not file.endswith(SIG_EXT):
                continue
            with open(file, 'rb') as ifile:
                sig = ifile.read()
                sig = zstd.decompress(sig).strip()
                sig = sig.split(b"\n")
                for line in sig:
                    sig_opcodes, name = line.split(" ")
                    func_sigs[sig_opcodes.strip()] = name.strip()
    # apply sigs
    counter = 0
    for sig_opcodes, addr in func_bytes_addr.items():
        if func_sigs.has_key(sig_opcodes):
            func_name = func_sigs[sig_opcodes]
            current_name = ida_funcs.get_func_name(addr)
            if (current_name == func_name):
                continue
            digit = 1
            while func_name in get_names():
                func_name = func_name + str(digit)
                digit = digit + 1
            ida_name.set_name(addr, func_name, ida_name.SN_NOCHECK)
            print("{}: {}".format(hex(addr), func_name))
            counter = counter + 1
            
    print("[idenLib] Applied to {} function(s)".format(counter))


class idenLib_class(idaapi.action_handler_t):
    def __init__(self):
        idaapi.action_handler_t.__init__(self)
    def activate(self, ctx):
        idenLib()
        return 1
    def update(self, ctx):
        return idaapi.AST_ENABLE_FOR_WIDGET if ctx.widget_type == idaapi.BWN_DISASM else idaapi.AST_DISABLE_FOR_WIDGET

# icon author: https://www.flaticon.com/authors/freepik
icon_data = "".join([
    "\x89\x50\x4E\x47\x0D\x0A\x1A\x0A\x00\x00\x00\x0D\x49\x48\x44\x52\x00\x00\x00\x18\x00\x00\x00\x18\x08\x03\x00\x00\x00\xD7\xA9\xCD\xCA\x00\x00\x00\x4E\x50\x4C\x54\x45\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xC4\xA2\xA6\x59\x00\x00\x00\x19\x74\x52\x4E\x53\x00\x20\xEE\x4F\xC9\x64\xD3\xB3\x32\x99\x88\x17\x0C\xC1\x5C\x28\xF6\x7F\xE6\xDD\xBB\xA2\x47\x41\x90\xCE\x19\x07\xA1\x00\x00\x00\xC8\x49\x44\x41\x54\x28\xCF\x75\xD1\xDB\xAE\x83\x20\x10\x85\xE1\x35\x08\x0E\xCA\x16\x3C\xDB\xF5\xFE\x2F\xBA\xC7\x58\xDB\xB4\xA1\xFF\x8D\xC8\x27\x48\x02\x7E\x26\xD6\xDF\xE7\x58\x70\x46\xAB\x79\x82\x23\x19\xD4\x31\x55\xC1\x93\x47\x75\xAB\xFD\x10\xA9\xAE\x38\x16\xEA\x0B\x36\x6F\x6D\x88\x56\x8A\xE4\xFC\x02\xA5\xA5\x58\x9C\x73\x19\x23\x99\x6E\x88\x12\xA3\x94\x6B\x2B\x78\x9B\xB8\xA1\xA5\x9B\xE9\x9F\xF0\x20\xA7\x37\x58\x37\x64\x52\xAB\x50\x48\x57\x85\xF3\x21\x55\x18\x6C\xA6\x0A\x3D\xD9\x1B\x68\x37\x7E\x41\xD3\x4E\x0A\x2C\x40\xF7\x05\x12\x60\x2B\x5C\xC2\x70\x43\x0E\x21\x14\xD8\x97\xD0\x02\x8E\xB3\xFD\xA3\x1D\xD4\x0F\xD0\x75\x5D\x77\x03\x1D\x99\xD1\x5B\x25\xED\x21\x34\x09\x93\x8D\xA3\x41\x9E\xEC\xA5\xB3\xA2\xBF\xB6\x7A\xD8\xF8\x04\xD9\xDA\xA1\x76\x5C\x24\x3A\xBD\x6E\x4D\xCE\xD2\xFB\x36\x05\xBF\xFB\x07\x19\xFC\x16\xA4\x38\xC6\x08\x3D\x00\x00\x00\x00\x49\x45\x4E\x44\xAE\x42\x60\x82"
])

class idenLibMain(idaapi.plugin_t):
    flags = idaapi.PLUGIN_UNL
    comment = "idenLib - Library Function Identification"
    help = "Contact: Lasha Khasaia (@_qaz_qaz)"
    wanted_name = PLUGIN_NAME
    wanted_hotkey = ''

    def run(self, arg):
        idenLib()
        pass

    def term(self):
        pass

    def init(self):
        act_icon = idaapi.load_custom_icon(data=icon_data, format="png")
        act_name = "idenLib:action"
        idaapi.register_action(idaapi.action_desc_t(
                act_name,
                "idenLib",
                idenLib_class(),
                None,
                "idenLib",
                act_icon))
        # Insert the action in a toolbar
        idaapi.attach_action_to_toolbar("DebugToolBar", act_name)
        return idaapi.PLUGIN_OK



def PLUGIN_ENTRY():
    return idenLibMain()

if __name__ == "__main__":
    PLUGIN_ENTRY()