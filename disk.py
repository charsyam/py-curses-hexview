import sys
import binascii
import struct
from py3 import PY3

class Disk:
    f = None

    def __init__(self, block_size, filename):
        self.block_size = block_size
        self.open(filename)

    def open(self, filename):
        if PY3:
            self.f = open(filename, encoding='latin1')
        else:
            self.f = open(filename)

        return self.f

    def seek(self, lba):
        self.f.seek(lba*self.block_size)

    def read(self, lba, size):
        self.seek(lba)
        return self.f.read(self.block_size * size)

    def size(self):
        self.f.seek(0, 2)
        return self.f.tell()

if __name__ == "__main__":
    disk = Disk(512, sys.argv[1])
    print(disk.size())

