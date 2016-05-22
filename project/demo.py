
import struct

str = "11010"

f = open("demo", "wb+")
f.write(struct.pack('B', int(str, 2)))
f.close()


f = open("demo","rb")
struct.unpack('B', f.read(1))
f.close()


