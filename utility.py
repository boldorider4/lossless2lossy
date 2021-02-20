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
