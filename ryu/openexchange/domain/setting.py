'''
This module is about domain setting

Author:www.muzixing.com
Date                Work
2015/7/29           new this file
2015/7/29           Finish.

'''
from ryu import cfg
from ryu.openexchange import oxproto_common


CONF = cfg.CONF


config = {'flags': CONF.oxp_flags,
          'period': CONF.oxp_period,
          'miss_send_len': CONF.oxp_miss_send_len, }


features = {'domain_id': CONF.oxp_domain_id,
            'sbp_version': CONF.sbp_proto_version,
            'proto_type': CONF.sbp_proto_type,
            'capabilities': CONF.oxp_capabilities,
            }

# CONF.oxp_flags

domain_function = {oxproto_common.OXP_ADVANCED_HOP: 'floyd_dict',
                   oxproto_common.OXP_SIMPLE_HOP: 'floyd_dict',
                   oxproto_common.OXP_ADVANCED_BW: None,
                   oxproto_common.OXP_SIMPLE_BW: None}

super_function = {oxproto_common.OXP_ADVANCED_HOP: 'full_floyd_dict',
                  oxproto_common.OXP_SIMPLE_HOP: 'floyd_dict',
                  oxproto_common.OXP_ADVANCED_BW: None,
                  oxproto_common.OXP_SIMPLE_BW: None}


def function(flags):
    if CONF.oxp_role == 'domain':
        return domain_function[flags]
    if CONF.oxp_role == 'super':
        return super_function[flags]
    else:
        return
