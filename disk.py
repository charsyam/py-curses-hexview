import sys
import binascii
import struct
from py3 import PY3

class Disk:
    READ_BINARY_MODE = "rb"

    def __init__(self, block_size, filename, filesize):
        self.block_size = block_size
        self.f = open(filename, Disk.READ_BINARY_MODE)
        self.filesize = filesize

    def seek(self, lba):
        self.f.seek(lba*self.block_size)

    def read(self, lba, size):
        self.seek(lba)
        return self.f.read(self.block_size * size)

    def block_count(self):
        return int((self.size() + self.block_size- 1) / self.block_size)

    def size(self):
        return self.filesize
