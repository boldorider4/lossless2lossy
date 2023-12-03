#!/usr/bin/python3

import argparse
import literals

from cuefile import Cuefile
from tagging import Tagging
from utility import check_tools
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
        self.cuefile_encoding = literals.utf_8
        self.single_lossless_file = None
        self.args = args
        self.single_lossless_file = None
        self.decode_tools = { literals.flac : [literals.flac],
                              literals.shntool : [literals.shntool, 'split', '-o', 'wav', '-O', 'always'],
                              literals.ffmpeg : [literals.ffmpeg],
                              literals.mac : [literals.mac],
                              literals.wvunpack : literals.wvunpack }
        self.encode_tools = { literals.ffmpeg : [literals.ffmpeg],
                              literals.afconvert : [literals.afconvert, '-v', '-d', 'aac', '-f', 'm4af', '-u', 'pgcm', '2', '-q',
                                                    '127', '-s', '2', '--soundcheck-generate'] }
        self.other_tools = { literals.mp4box : [literals.mp4box],
                             literals.ffmpeg : [literals.ffmpeg],
                             literals.atomicparsley : [literals.atomicparsley, '--overWrite'] }
        self.decoder = literals.ffmpeg
        self.encoder = literals.ffmpeg
        self.splitter = literals.shntool
        self.tagger = literals.atomicparsley


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


def main():
    args = parser()
    config = ConvertConfig(args=args)
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
        album_tags = tagging.get_album_tags_from_cuefile(cuefile)
        cuefile.extract_single_lossless_file()

    codec.decode_input_files(album_tags, cuefile)
    codec.convert_files(album_tags)
    return 0


if __name__ == '__main__':
    main()
