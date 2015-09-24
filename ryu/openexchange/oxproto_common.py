"""
This file define the common field of oxp.
Author:www.muzixing.com

"""

from struct import calcsize


OXP_HEADER_PACK_STR = '!BBHI'
OXP_HEADER_SIZE = 8
assert calcsize(OXP_HEADER_PACK_STR) == OXP_HEADER_SIZE

# We set the port 6688 as OXP's port.
OXP_TCP_PORT = 6688
OXP_SSL_PORT = 6688

# default config information
OXP_DEFAULT_FLAGS = 2

OXP_SIMPLE_BW = 2
OXP_SIMPLE_HOP = 8

OXP_ADVANCED_BW = 3
OXP_ADVANCED_HOP = 9

OXP_DEFAULT_K_PATH = 2

# 10 minutes
OXP_DEFAULT_PERIOD = 15
OXP_MAX_PERIOD = 30

OXP_DEFAULT_MISS_SEND_LEN = 128
OXP_DEFAULT_PROTO_TYPE = 1
# default features information
OXP_DEFAULT_DOMAIN_ID = 1
OXP_DEFAULT_CAPABILITIES = 127

OXP_MAX_LEN = 10000
OXP_MAX_CAPACITY = 281474976710655L
