#SNMP versions
SNMP_VER1 = 0x00

#ASN.1 primitives
ASN1_INT = 0x02
ASN1_OCTSTR = 0x04 #OctetString
ASN1_OID = 0x06 #ObjectIdentifier
ASN1_NULL = 0x05
ASN1_SEQ = 0x30 #sequence

#SNMP specific SEQUENCE types
SNMP_GETREQUEST = 0xa0
SNMP_GETRESPONSE = 0xa2
SNMP_GETNEXTREQUEST = 0xa1

#SNMP specific integer types
SNMP_COUNTER = 0x41
SNMP_GUAGE = 0x42
SNMP_TIMETICKS = 0x43

#SNMP specific other types
SNMP_IPADDR = 0x40
SNMP_OPAQUE = 0x44 #not handled
SNMP_NSAPADDR = 0x45 #not handled

#SNMP error codes
SNMP_ERR_NOERROR = 0x00
SNMP_ERR_TOOBIG = 0x01
SNMP_ERR_NOSUCHNAME = 0x02
SNMP_ERR_BADVALUE = 0x03
SNMP_ERR_READONLY = 0x04
SNMP_ERR_GENERR = 0x05

class GetRequest():
    #should request classes derive from "SnmpPacket" or similar?
    def __init__(self, data=None, \
                       ver=SNMP_VER1, community="public", request_id=1, mibs=[]
                ):
        if type(data) is bytearray:
            self._rawpacket = data
            unpacked = unpack(data)
            self.ver = unpacked[1][1]
            self.community = unpacked[2][1]
            self.request_id = unpacked[3][1][1]
            self.error_status = unpacked[3][2][1]
            self.index = unpacked[3][3][1]
            if self.error_status == SNMP_ERR_NOERROR:
                self.mibs = []
                for seq in unpacked[3][4][1:]:
                    self.mibs.append(seq[1][1])
        else:
            self.ver = ver
            self.community = community
            self.request_id = request_id
            self.error_status = SNMP_ERR_NOERROR
            self.index = 0
            self.mibs = mibs

def pack(packet):
    pass

def pack_tlv(t, v):
    b=bytearray()
    #sequence types
    if t in (ASN1_SEQ, SNMP_GETREQUEST, SNMP_GETRESPONSE):
        for block in v:
            b.extend(block)
    #octet string
    elif t == ASN1_OCTSTR:
        b = bytearray(map(ord, v))
    #integer types
    elif t in (ASN1_INT, SNMP_COUNTER, SNMP_GUAGE, SNMP_TIMETICKS):
        #can't encode -ve values
        #do -ve values occur in snmp?
        if v < 0:
            raise Exception("SNMP, -ve int")
        else:
            b.append(v & 0xff)
            v //= 0x100
            while v > 0:
                b = bytearray([v & 0xff]) + b
                v //= 0x100
            #+ve values with high 0rder bit set are prefixed by 0x0
            #observed in snmp, indicating -ve snmp ints are possible?
            if b[0]&0x80==0x80:
                b = bytearray([0x0]) + b
    elif t == ASN1_NULL:
        l = 0x0
    elif t == ASN1_OID:
        oid = v.split(".")
        oid = list(map(int, oid))
        #first two indexes are encoded in single byte
        b.append(oid[0]*40 + oid[1])
        for id in oid[2:]:
            if 0 <= id < 0x7f:
                b.append(id)
                #check RFC's for correct upperbound
            elif 0x7f < id < 0x7fff:
                b.append(id//0x80+0x80)
                b.append(id&0x7f)
            else:
                raise Exception("SNMP, OID value out of range")
    elif t == SNMP_IPADDR:
        for byte in map(int, v.split(".")):
            b.append(byte)
    elif t in (SNMP_OPAQUE, SNMP_NSAPADDR):
        raise Exception("SNMP, OPAQUE and NSAPADDR encoding not implemented")
    return bytearray([t]) + pack_len(len(b)) + b

def unpack(b):
    ptr = 0
    t,l,v = unpack_tlv(b)
    if type(v) is list:
        packet = [t]+v
    else:
        packet = [t,v]
    if type(v) is bytearray:
        packet[1] = unpack(v)
    elif type(v) is list:
        for i,val in enumerate(packet[1:]):
            packet[1+i] = unpack(val)
    return packet

def unpack_tlv(b):
    #should this return length of data, or of v?
    ptr = 0
    t = b[ptr]
    l, l_incr = unpack_len(b)
    ptr +=  1 + l_incr
    #sequence types
    if t in (ASN1_SEQ, SNMP_GETREQUEST, SNMP_GETRESPONSE):
        v = []
        while ptr < len(b):
            lb, lb_incr = unpack_len( b[ptr:] )
            v.append( b[ptr : ptr+1+lb_incr+lb] )
            ptr += 1 + lb + lb_incr
    #octet string
    elif t == ASN1_OCTSTR:
        #v = b[ptr : ptr+l].decode()
        #no bytearray.decode in micropython
        v = bytes(b[ptr : ptr+l]).decode()
    #integer types
    elif t in (ASN1_INT, SNMP_COUNTER, SNMP_GUAGE, SNMP_TIMETICKS):
        #can't decode -ve values
        #do -ve values occur in snmp?
        v=0
        for byte in b[ptr:]:
            v = v*0x100 + byte
    elif t == ASN1_NULL:
        if b[1]==0 and len(b)==2:
            v=None
        else:
            raise Exception("SNMP, bad null encoding")
    elif t == ASN1_OID:
        #first 2 indexes are encoded in single byte
        v = str( b[ptr]//0x28 ) + "." + str( b[ptr]%0x28 )
        ptr += 1
        high_septet = 0
        for byte in b[ptr:]:
            if byte&0x80 == 0x80:
                high_septet = byte - 0x80
            else:
                v += "." + str(high_septet*0x80 + byte)
                high_septet = 0
    elif t == SNMP_IPADDR:
        v = str(b[ptr])
        for byte in b[ptr+1:]:
            v += "." + str(byte)
    elif t in (SNMP_OPAQUE, SNMP_NSAPADDR):
        raise Exception("SNMP,OPAQUE and NSAPADDR decoding not implemented")
    else:
        raise Exception("SNMP invalid block code to decode")
    return t, 1+l+l_incr, v

def pack_len(l):
    #msdn.microsoft.com/en-us/library/windows/desktop/bb648641(v=vs.85).aspx
    #indicates encoding that differs from observation, for snmp
    #length of 0 valid for ASN1_NULL type
    if 0 <= l < 0x7f:
        return bytearray([l])
    #check RFC's for correct upperbound
    elif 0x7f < l < 0x7fff:
        return bytearray([l//0x80+0x80, l&0x7f])
    else:
        raise Exception("SNMP, length out of bounds")

def unpack_len(v):
    #msdn.microsoft.com/en-us/library/windows/desktop/bb648641(v=vs.85).aspx
    #indicates encoding that differs from observation, for snmp
    ptr=1
    if v[ptr]&0x80 == 0x80:
        return ((v[ptr]-0x80)*0x80) + v[ptr+1], 2
    else:
        return v[ptr], 1
