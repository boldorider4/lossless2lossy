import argparse
import subprocess
import os
import re


class ConvertConfig:
    def __init__(self, args=None):
        self.decode_tools = dict()
        self.encode_tools = dict()
        self.other_tools = dict()
        self.decoder = ''
        self.encoder = ''
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


def create_config(args=None):
    config = ConvertConfig(args)
    config.decode_tools = { 'flac_bin' : 'flac',
                            'mac_bin' : 'mac',
                            'wvunpack_bin' : 'wvunpack' }
    config.encode_tools = { 'ffmpeg_bin' : 'ffmpeg',
                            'afconvert_bin' : 'afconvert' }
    config.other_tools = { 'ack_bin' : 'ack',
                           'ssed_bin' : 'ssed',
                           'shntool_bin' : 'shntool',
                           'mp4box_bin' : 'mp4box',
                           'ffmpeg_bin' : 'ffmpeg',
                           'cueprint_bin' : 'cueprint' }
    config.decoder = 'ffmpeg_bin'
    config.encoder = 'afconvert_bin'
    return config


def check_tools(config):
    
    # check other tools
    for tool in config.other_tools.values():
        proc = subprocess.Popen(['which',tool],stdout=subprocess.PIPE)
        if len(proc.stdout.readlines()) == 0:
            print('{} is missing and is required'.format(tool))
            return False        

    # check decode tools
    is_any_tool_installed = False
    for tool in config.decode_tools.values():
        proc = subprocess.Popen(['which',tool],stdout=subprocess.PIPE)
        is_any_tool_installed |= (len(proc.stdout.readlines()) > 0)
    if not is_any_tool_installed:
        error_msg = 'neither of '
        for tool in config.decode_tools.values():
            error_msg += tool + ' '
        error_msg += 'is installed'
        print(error_msg)
        return False

    # check encode tools
    is_any_tool_installed = False
    for tool in config.encode_tools.values():
        proc = subprocess.Popen(['which',tool],stdout=subprocess.PIPE)
        is_any_tool_installed |= (len(proc.stdout.readlines()) > 0)
    if not is_any_tool_installed:
        error_msg = 'neither of '
        for tool in config.encode_tools.values():
            error_msg += tool + ' '
        error_msg += 'are installed'
        print(error_msg)
        return False

    return True


def select_cuefile(cuefile=None):
    cwd = os.getcwd()
    if cuefile:
        if os.path.exists(os.path.join(cwd, cuefile)):
            return (0, cuefile)
        else:
            print('selected cuefile does not exist')
            return (-1, '')
    else:
        print('guessing cufile to use...')
        candidates = [f for f in os.listdir(cwd) if f.endswith('.cue')]
        if len(candidates) == 1:
            cuefile = os.path.join(cwd, candidates[0])
            print('found cuefile {}'.format(cuefile))
            return (0, cuefile)
        elif len(candidates) > 1:
            print('ambiguous cuefiles...')
            return (-1, '')
        else:
            print('no cuefile present in dir')
            return (1, '')


def get_album_tags_from_cuefile(cuefile, config):
    tag_dict = dict()

    cue_info = subprocess.Popen([config.other_tools['cueprint_bin'], cuefile],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

    n_track = None
    album = None
    global_artist = None
    global_genre = None
    year = None

    for line in cue_info.readlines():
        n_tracks_match = re.match(r'^ *\t*no. of tracks: *\t*([0-9]+) *$', line.decode('utf-8'), re.IGNORECASE)
        if n_tracks_match is not None and n_track is None:
            n_track = int(n_tracks_match.group(1))
            continue

        artist_match = re.match(r'^ *\t*performer: *\t*(.*) *$', line.decode('utf-8'), re.IGNORECASE)
        if artist_match is not None and global_artist is None:
            global_artist = artist_match.group(1)
            continue

        album_match = re.match(r'^ *\t*title: *\t*(.*) *$', line.decode('utf-8'), re.IGNORECASE)
        if album_match is not None and album is None:
            album = album_match.group(1)
            continue

        genre_match = re.match(r'^ *\t*genre: *\t*(.*) *$', line.decode('utf-8'), re.IGNORECASE)
        if genre_match is not None and global_genre is None:
            global_genre = genre_match.group(1)
            continue

    if n_track is None:
        return tag_dict

    with open(cuefile) as cuefile_fd:
        for cuefile_line in cuefile_fd.readlines():
            year_match = re.match(r'^ *\t*(REM )?DATE *\t*([0-9]*) *$', cuefile_line, re.IGNORECASE)
            if year_match is not None:
                year = int(year_match.group(2))
                break

    for track in range(1, n_track+1):
        cue_info = subprocess.Popen([config.other_tools['cueprint_bin'], cuefile, '-n', str(track)],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout

        artist = None
        title = None
        genre = None
        for line in cue_info.readlines():
            # 'perfomer' is a mispelling due to a bug in cueprint
            artist_match = re.match(r'^ *\t*perfomer: *\t*(.*) *$', line.decode('utf-8'), re.IGNORECASE)
            if artist_match is not None:
                artist = artist_match.group(1)
                if artist == '':
                    artist = global_artist
                continue

            title_match = re.match(r'^ *\t*title: *\t*(.*) *$', line.decode('utf-8'), re.IGNORECASE)
            if title_match is not None:
                title = title_match.group(1)
                continue

            genre_match = re.match(r'^ *\t*genre: *\t*(.*) *$', line.decode('utf-8'), re.IGNORECASE)
            if genre_match is not None:
                genre = genre_match.group(1)
                if genre == '':
                    genre = global_genre
                continue

        track_tag_dict = dict()
        track_tag_dict['artist'] = artist
        track_tag_dict['album'] = album
        track_tag_dict['year'] = year
        track_tag_dict['title'] = title
        track_tag_dict['genre'] = genre
        if 1 not in tag_dict:
            tag_dict[1] = dict()
        tag_dict[1][track] = track_tag_dict

    return tag_dict


def get_album_tags_from_dir(config):
    cwd = os.getcwd()
    audio_source_files = [f for f in os.listdir(cwd) if f.endswith('.ape')
                          or f.endswith('.wv')
                          or f.endswith('.flac')]
    tag_dict = dict()

    for track_file in audio_source_files:
        artist = None
        album = None
        year = None
        disctotal = None
        title = None
        genre = None
        track = None

        if config.decoder == 'ffmpeg_bin':
            decode_stderr = subprocess.Popen(
                [config.other_tools[config.decoder], '-i', track_file, '-y', '-f', 'ffmetadata'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE).stderr

            for line in decode_stderr.readlines():
                artist_match = re.match(r'^ +ARTIST +: +(.*)$', line.decode('utf-8'), re.IGNORECASE)
                if artist_match is not None:
                    artist = artist_match.group(1)
                    continue

                album_match = re.match(r'^ +ALBUM +: +(.*)$', line.decode('utf-8'), re.IGNORECASE)
                if album_match is not None:
                    album = album_match.group(1)
                    continue
                year_match = re.match(r' +DATE +: +([0-9][0-9][0-9][0-9]).?[0-9]?.?[0-9]?',
                                      line.decode('utf-8'), re.IGNORECASE) 
                if year_match is not None:
                    year = int(year_match.group(1))
                    continue

                disctotal_match = re.match(r'^ +DISCTOTAL +: +([0-9]+)$', line.decode('utf-8'),
                                           re.IGNORECASE)
                if disctotal_match is not None:
                    disctotal = int(disctotal_match.group(1))
                    continue

                title_match = re.match(r'^ +title +: +(.*)$', line.decode('utf-8'), re.IGNORECASE)
                if title_match is not None:
                    title = title_match.group(1)
                    continue

                genre_match = re.match(r'^ +GENRE +: +(.*)$', line.decode('utf-8'), re.IGNORECASE)
                if genre_match is not None:
                    genre = genre_match.group(1)
                    continue

                track_match = re.match(r'^ +track +: +(.*)$', line.decode('utf-8'), re.IGNORECASE)
                if track_match is not None:
                    track = int(track_match.group(1))
                    continue
        else:
            raise NotImplementedError()

        track_tag_dict = dict()
        track_tag_dict['artist'] = artist
        track_tag_dict['album'] = album
        track_tag_dict['year'] = year
        track_tag_dict['title'] = title
        track_tag_dict['genre'] = genre
        if disctotal not in tag_dict:
            tag_dict[disctotal] = dict()
        tag_dict[disctotal][track] = track_tag_dict

    return tag_dict


def main():
    args = parser()
    config = create_config(args=args)
    # check = check_tools(config)
    check = True

    if not check:
        return -1

    ret = select_cuefile(args.cuefile)
    album_tags = None

    if ret[0] == 1:
        print('trying file by file mode...')
        album_tags = get_album_tags_from_dir(config)
    elif ret[0] == -1:
        return -1
    elif ret[0] == 0:
        album_tags = get_album_tags_from_cuefile(ret[1], config)

    print(album_tags)
    return 0


if __name__ == '__main__':
    main()
