#!/usr/bin/python3

import argparse
import subprocess
import unicodedata
import os
import re

from cuefile import Cuefile


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


def decode_input_files(config, tag_dict, cuefile=None, single_lossless_file=None):
    if config.single_lossless_file:
        print('A single lossless file was found! Splitting it...')
        decode_cmd = config.decode_tools[config.splitter].copy()

        if config.splitter == 'shntool_bin':
            decode_cmd.append('-f')
            decode_cmd.append(cuefile)
            decode_cmd.append('-d')
            decode_cmd.append('.')
            decode_cmd.append(single_lossless_file)

        return [subprocess_popen(decode_cmd)]
    elif 1 not in tag_dict:
        print('No files containing tags found! Leaving decode function...')
        exit(-1)
    else:
        print('The referenced cuefile contains multiple files. Converting one by one...')

        decode_stdout = list()

        for disc in tag_dict:
            for n_track, track in tag_dict[disc].items():
                try:
                    losslessfile = track['losslessfile']
                except KeyError as key_error:
                    print('the tag dict does not contain a losslessfile field in each track...')
                    raise key_error

                infile = track['infile']
                print('converting {} to {}'.format(losslessfile, infile))

                decode_cmd = config.decode_tools[config.decoder].copy()
                if config.decoder == 'ffmpeg_bin':
                    decode_cmd.append('-i')
                    decode_cmd.append(losslessfile)
                    decode_cmd.append('-y')
                    decode_cmd.append(infile)

                decode_stdout.append(subprocess_popen(decode_cmd))
        return decode_stdout


def compose_converter_cmd(config, tags, dir_name):
    infile = tags['infile']
    outfile = os.path.join(dir_name, tags['outfile'])
    if config.args.bitrate is None:
        bitrate = str(256000)
    else:
        bitrate = config.args.bitrate

    if config.encoder == 'afconvert_bin':
        encoder_cmd = config.encode_tools[config.encoder].copy()
        encoder_cmd.append('-b')
        encoder_cmd.append(bitrate)
        encoder_cmd.append(infile)
        encoder_cmd.append(outfile)
    elif config.encoder == 'ffmpeg_bin':
        encoder_cmd = config.encode_tools[config.encoder].copy()
        encoder_cmd.append(infile)
        encoder_cmd.append(outfile)
    else:
        raise NotImplementedError()
    return encoder_cmd


def append_option_to_cmd(cmd, option, tag):
    if tag is not None and isinstance(tag, str) and tag != '':
        cmd.append(option)
        cmd.append(tag)


def compose_tagger_cmd(config, track, n_tracks, disc, n_discs, tags, dir_name):
    outfile = os.path.join(dir_name, tags['outfile'])

    tagger_cmd = config.other_tools[config.tagger].copy()
    if config.tagger == 'atomicparsley_bin':
        tagger_cmd.insert(1, outfile)
        tagger_cmd.append('--tracknum')
        tagger_cmd.append(str(track) + '/' + str(n_tracks))
        append_option_to_cmd(tagger_cmd, '--title', tags['title'])
        append_option_to_cmd(tagger_cmd, '--artist', tags['artist'])
        append_option_to_cmd(tagger_cmd, '--album', tags['album'])
        append_option_to_cmd(tagger_cmd, '--genre', tags['genre'])
        append_option_to_cmd(tagger_cmd, '--year', tags['year'])
        append_option_to_cmd(tagger_cmd, '--comment', tags['comment'])
        if n_discs > 1 or (config.args.discs is not None and config.args.discs > 1):
            tagger_cmd.append('--disk')
            if config.args.disc is not None:
                disc = config.args.disc
            if config.args.discs is not None:
                n_discs = config.args.discs
            tagger_cmd.append(str(disc) + '/' + str(n_discs))
        if config.args.cover is not None:
            tagger_cmd.append('--artwork')
            tagger_cmd.append(config.args.cover)
    else:
        raise NotImplementedError()

    return tagger_cmd


def convert_files(album_tags, config):
    if 1 not in album_tags:
        print('No files containing tags found! Leaving convert function...')
        exit(-1)

    if config.args.path is not None and os.path.isdir(config.args.path):
        dir_name = config.args.path
    else:
        dir_name = os.getcwd()

    global_album = album_tags[1][1]['album']
    dir_name = os.path.join(dir_name, global_album)
    try:
        os.stat(dir_name)
    except:
        os.mkdir(dir_name)

    n_discs = len(album_tags)
    tagging_subprocess = list()
    converting_subprocess = list()
    for disc, tracktags in album_tags.items():
        n_tracks = len(tracktags)
        for track, tags in tracktags.items():
            print()
            print('converting track {}/{} of disc {}/{}...cmd line is'.format(track, n_tracks, disc, n_discs))

            converter_cmd = compose_converter_cmd(config, tags, dir_name)
            output_cmd = ''
            for param in converter_cmd:
                output_cmd += param + ' '
            print(output_cmd)

            converting_subprocess.append(subprocess_popen(converter_cmd))

    for convert_subprocess in converting_subprocess:
        convert_subprocess.wait()

    for disc, tracktags in album_tags.items():
        n_tracks = len(tracktags)
        for track, tags in tracktags.items():
            print()
            print('cleaning up temp file...')
            os.remove(tags['infile'])

            print('taggin track track {}/{} of disc {}/{}...'.format(track, n_tracks, disc, n_discs))

            tagger_cmd = compose_tagger_cmd(config, track, n_tracks, disc, n_discs, tags, dir_name)
            output_cmd = ''
            for param in tagger_cmd:
                output_cmd += param + ' '
            print(output_cmd)
            tagging_subprocess.append(subprocess_popen(tagger_cmd))

    for tagging_subproc in tagging_subprocess:
        tagging_subproc.wait()

    if config.args.cover is not None and config.tagger == 'atomicparsley_bin':
        cover_filename, cover_ext = os.path.splitext(config.args.cover)
        cover_residue = os.path.basename(cover_filename + '-resized')
        for filename in os.listdir(os.getcwd()):
            if filename.startswith(cover_residue) and (filename.endswith('.jpeg') or \
                                                        filename.endswith('.jpg') or \
                                                        filename.endswith('.png') or filename.endswith(cover_ext)):
                os.remove(filename)


def main():
    args = parser()
    config = create_config(args=args)
    cuefile = Cuefile(config=config)
    check = check_tools(config)

    if not check:
        return -1

    ret = cuefile.select_cuefile()
    album_tags = None

    if ret[0] == 1:
        print('trying file by file mode...')
        album_tags = get_album_tags_from_dir(config)
        piped_subprocess = decode_input_files(config, album_tags)
    elif ret[0] == 0:
        cuefile = ret[1]
        album_tags = get_album_tags_from_cuefile(cuefile, config)
        single_lossless_file = cuefile.extract_single_lossless_file()
        piped_subprocess = decode_input_files(config, album_tags, cuefile, single_lossless_file)
    for process in piped_subprocess:
        process.wait()

    convert_files(album_tags, config)
    return 0


if __name__ == '__main__':
    main()
