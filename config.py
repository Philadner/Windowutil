import configparser
import os

config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))

# Access config values
#animation
ANIM_ENABLED = config.getboolean('animation', 'enabled', fallback=True)
ANIM_DURATION = config.getfloat('animation', 'duration', fallback=0.4)
ANIM_STEPS = config.getint('animation', 'steps', fallback=100 * int(ANIM_DURATION) + 100)
EASING_TYPE = config.get('animation', 'easing', fallback='easeInOutQuad')

#nudge
DEFAULT_NUDGE_STRENGTH = config.getint('nudge', 'default_strength', fallback=50)

#debug
RETURN_SPLITCMD = config.getboolean('debug', 'return_splitcmd', fallback=False)
RETURN_CONFIG = config.getboolean('debug', 'return_config', fallback=False)
RETURN_DURATION = config.getboolean('debug', 'return_duration', fallback=False)