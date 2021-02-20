import os
import re
import subprocess
import unicodedata


def subprocess_popen(cmd):
    try:
        env_path = dict()
        env_path['PATH'] = os.environ['PATH']
        env_path['PATH'] = '/usr/local/bin:' + env_path['PATH']
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env_path, shell=False)
    except FileNotFoundError as file_not_found_error:
        print('something went wrong when trying to run {}'.format(cmd))
        print(file_not_found_error)
        exit(-1)


def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')


def check_tools(config):
    # check other tools
    for tool in config.other_tools.values():
        proc = subprocess_popen(['which',tool[0]])
        proc.wait()
        if len(proc.stdout.readlines()) == 0:
            print('{} is missing and is required'.format(tool[0]))
            return False

    # check decode tools
    is_any_tool_installed = False
    for tool in config.decode_tools.values():
        proc = subprocess_popen(['which',tool[0]])
        proc.wait()
        is_any_tool_installed |= (len(proc.stdout.readlines()) > 0)
    if not is_any_tool_installed:
        error_msg = 'neither of '
        for tool in config.decode_tools.values():
            error_msg += tool[0] + ' '
        error_msg += 'is installed'
        print(error_msg)
        return False

    # check encode tools
    is_any_tool_installed = False
    for tool in config.encode_tools.values():
        proc = subprocess_popen(['which',tool[0]])
        proc.wait()
        is_any_tool_installed |= (len(proc.stdout.readlines()) > 0)
    if not is_any_tool_installed:
        error_msg = 'neither of '
        for tool in config.encode_tools.values():
            error_msg += tool[0] + ' '
        error_msg += 'are installed'
        print(error_msg)
        return False

    return True
