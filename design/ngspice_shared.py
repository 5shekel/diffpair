"""Small synchronous adapter for the ngspice DLL bundled with KiCad 10.

ABI source: ngspice sharedspice.h, retained in design/references.
Only passive circuit analysis is used here; no background worker is started.
"""
from pathlib import Path
import ctypes as C
import os
import numpy as np

class Complex(C.Structure):
    _fields_=[('real',C.c_double),('imag',C.c_double)]

class Vector(C.Structure):
    _fields_=[('name',C.c_char_p),('type',C.c_int),('flags',C.c_short),
              ('real',C.POINTER(C.c_double)),('complex',C.POINTER(Complex)),('length',C.c_int)]

class NgSpice:
    def __init__(self,path=Path(r'C:\Program Files\KiCad\10.0\bin\ngspice.dll')):
        self.path=Path(path)
        self.dll_dir=os.add_dll_directory(str(self.path.parent))
        self.lib=C.CDLL(str(self.path)); self.log=[]; self.failed_exit=False
        output=C.CFUNCTYPE(C.c_int,C.c_char_p,C.c_int,C.c_void_p)
        exited=C.CFUNCTYPE(C.c_int,C.c_int,C.c_bool,C.c_bool,C.c_int,C.c_void_p)
        def write(msg,ident,user):
            self.log.append(msg.decode('utf-8',errors='replace')); return 0
        def stop(status,immediate,quit,ident,user):
            self.failed_exit=True; self.log.append(f'controlled_exit status={status}'); return 0
        self.callbacks=[output(write),exited(stop)]
        self.lib.ngSpice_Init.argtypes=[C.c_void_p]*7
        self.lib.ngSpice_Init.restype=C.c_int
        self.lib.ngSpice_Command.argtypes=[C.c_char_p]; self.lib.ngSpice_Command.restype=C.c_int
        self.lib.ngSpice_Circ.argtypes=[C.POINTER(C.c_char_p)]; self.lib.ngSpice_Circ.restype=C.c_int
        self.lib.ngGet_Vec_Info.argtypes=[C.c_char_p]; self.lib.ngGet_Vec_Info.restype=C.POINTER(Vector)
        if self.lib.ngSpice_Init(self.callbacks[0],None,self.callbacks[1],None,None,None,None):
            raise RuntimeError('ngspice initialization failed')
        self.command('set nomoremode')
        self.command('version')

    def command(self,command):
        start=len(self.log)
        code=self.lib.ngSpice_Command(command.encode('ascii'))
        messages=self.log[start:]
        if code or self.failed_exit or any('error:' in s.lower() or 'fatal' in s.lower() for s in messages):
            raise RuntimeError('\n'.join(messages))

    def circuit(self,text):
        self.command('destroy all')
        lines=[line.encode('ascii') for line in text.splitlines()]
        array=(C.c_char_p*(len(lines)+1))(*lines,None)
        start=len(self.log); code=self.lib.ngSpice_Circ(array)
        if code or self.failed_exit or any('error:' in s.lower() for s in self.log[start:]):
            raise RuntimeError('\n'.join(self.log[start:]))

    def vector(self,name):
        ptr=self.lib.ngGet_Vec_Info(name.encode('ascii'))
        if not ptr:raise RuntimeError('Missing ngspice vector '+name)
        v=ptr.contents
        if v.length<=0:raise RuntimeError('Empty ngspice vector '+name)
        if bool(v.real):return np.ctypeslib.as_array(v.real,shape=(v.length,)).copy()
        if bool(v.complex):return np.array([complex(v.complex[i].real,v.complex[i].imag) for i in range(v.length)])
        raise RuntimeError('No data in vector '+name)
