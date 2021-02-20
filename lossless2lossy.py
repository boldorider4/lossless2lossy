#!/usr/bin/python3

import argparse
import os

from cuefile import Cuefile
from tagging import Tagging
from utility import subprocess_popen
from codec import Codec


class ConvertConfig:
    def __init__(self, args):
        self.decode_tools = dict()
        self.encode_tools = dict()
        self.other_tools = dict()
        self.decoder = ''
        self.encoder = ''
        self.splitter = ''
        self.tagger = ''
        self.cuefile_encoding = 'utf-8'
        self.single_lossless_file = None
        self.args = args
        self.single_lossless_file = None


def parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-q', '--cuefile', type=str, help='specifies the cuefile to use for track info')
    parser.add_argument('-c', '--cover', type=str, help='specifies the cover file')
    parser.add_argument('-y', '--year', type=str, help='sets the year')
    parser.add_argument('-g', '--genre', type=str, help='sets the genre')
    parser.add_argument('-a', '--album', type=str, help='sets the album')
    parser.add_argument('-p', '--performer', type=str, help='sets the performer')
    parser.add_argument('-k', '--comment', type=str, help='sets the comment')
    parser.add_argument('-n', '--disc', type=str, help='sets the disc number')
    parser.add_argument('-m', '--discs', type=str, help='sets the total number of discs')
    parser.add_argument('-b', '--bitrate', type=str, help='sets the bitrate')
    parser.add_argument('-d', '--path', type=str, help='sets the sets the output path for the converted files')
    args = parser.parse_args()
    return args


def create_config(args):
    config = ConvertConfig(args)
    config.decode_tools = { 'flac_bin' : ['flac'],
                            'shntool_bin' : ['shntool', 'split', '-o', 'wav', '-O', 'always'],
                            'ffmpeg_bin' : ['ffmpeg'],
                            'mac_bin' : ['mac'],
                            'wvunpack_bin' : 'wvunpack' }
    config.encode_tools = { 'ffmpeg_bin' : ['ffmpeg'],
                            'afconvert_bin' : ['afconvert', '-v', '-d', 'aac', '-f', 'm4af', '-u', 'pgcm', '2', '-q',
                                               '127', '-s', '2', '--soundcheck-generate'] }
    config.other_tools = { 'mp4box_bin' : ['mp4box'],
                           'ffmpeg_bin' : ['ffmpeg'],
                           'cueprint_bin' : ['cueprint'],
                           'atomicparsley_bin' : ['AtomicParsley', '--overWrite'] }
    config.decoder = 'ffmpeg_bin'
    config.encoder = 'afconvert_bin'
    config.splitter = 'shntool_bin'
    config.tagger = 'atomicparsley_bin'
    return config


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


def main():
    args = parser()
    config = create_config(args=args)
    cuefile = Cuefile(config=config)
    tagging = Tagging(config=config)
    codec = Codec(config=config)
    check = check_tools(config)

    if not check:
        return -1

    cuefile.select_cuefile()
    album_tags = None

    if cuefile.mode == 1:
        album_tags = tagging.get_album_tags_from_dir()
    elif cuefile.mode == 0:
        album_tags = tagging.get_album_tags_from_cuefile()
        config.single_lossless_file = cuefile.extract_single_lossless_file()

    codec.decode_input_files(album_tags, cuefile)
    codec.convert_files(album_tags)
    return 0


if __name__ == '__main__':
    main()
