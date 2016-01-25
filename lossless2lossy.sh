#!/bin/bash

# tools
ack_bin=$(which ack)
sed_bin=$(which ssed)
cueprint_bin=$(which cueprint)
ffmpeg_bin=$(which ffmpeg)
shntool_bin=$(which shntool)
afconvert_bin=$(which afconvert)
fdkaac_bin=$(which fdkaac)
atomicParsley_bin=$(which AtomicParsley)
mp4box_bin=$(which MP4Box)

# encoding options
bitrate="256000"
afconvert_opt='-v -d aac -f m4af -u pgcm 2 -q 127 -s 2 -b "$bitrate" --soundcheck-generate "$relative_path$wav_file" "$subdir$aac_file"'
fdkaac_opt='--profile 2 --bitrate-mode 0 --bitrate "$bitrate" --bandwidth 20000 --afterburner 1 -o "$subdir$aac_file" --ignorelength "$relative_path$wav_file"'

# tagging options
compilation=0
use_atomicparsley=0

function print_debug()
{
    echo album $album
    echo album_artist $album_artist
    echo performer $performer
    echo year $year
    echo genre $genre
    echo comment $comment
    echo bitrate $bitrate
    echo cuefile $cuefile
    echo cover $cover
    echo n_files $n_files
    echo n_tracks $n_tracks
    if [ -n "$disc_idx" ]
    then
        echo disc_idx $disc_idx
    fi
    if [ -n "$disc_tot" ]
    then
        echo disc_tot $disc_tot
    fi
}

function check_tools()
{
    local tools_missing=""
    local tools_missing_flag=0
    local codecs_missing=""
    local codecs_missing_flag=0
    local libraries_suggested=""
    local libraries_suggested_flag=0

    if [ -z "$ack_bin" ]
    then
        tools_missing+=" ack"
        tools_missing_flag=1
    fi
    if [ -z "$sed_bin" ]
    then
        tools_missing+=" ssed"
        tools_missing_flag=1
    fi
    if [ -z "$cueprint_bin" ]
    then
        tools_missing+=" cuetools"
        tools_missing_flag=1
    fi
    if [ -z "$ffmpeg_bin" ]
    then
        tools_missing+=" ffmpeg"
        tools_missing_flag=1
    fi
    if [ -z "$shntool_bin" ]
    then
        tools_missing+=" shntool"
        tools_missing_flag=1
    fi
    if [[ -z "$afconvert_bin" && -z "$fdkaac_bin" ]]
    then
        tools_missing+=" [afconvert|fdkaac]"
        tools_missing_flag=1
    fi
    if [[ -z "$atomicParsley_bin" && -z "$mp4box_bin" ]]
    then
        tools_missing+=" [AtomicParsley|mp4box]"
        tools_missing_flag=1
    fi
    if [ -z "$(which flac)" ]
    then
        codecs_missing+=" flac"
        codecs_missing_flag=1
    fi
    if [ -z "$(which mac)" ]
    then
        codecs_missing+=" mac"
        codecs_missing_flag=1
    fi
    if [ -z "$(which wvunpack)" ]
    then
        codecs_missing+=" wvunpack"
        codecs_missing_flag=1
    fi
    fdklib=$(find $(echo "$LIBRARY_PATH:$LD_LIBRARY_PATH" | tr ":" "\n") -maxdepth 1 -name 'libfdk-aac.so' -o -name 'libfdk-aac.dylib')
    if [ -z "$fdklib" ]
    then
        libraries_suggested+=" libfdk-aac(for fdkaac)"
        libraries_suggested_flag=1
    fi

    if [ $tools_missing_flag -eq 1 ]
    then
        echo the missing tools are:$tools_missing
    fi
    if [ $codecs_missing_flag -eq 1 ]
    then
        echo the missing codecs are:$codecs_missing
    fi
    if [ $libraries_suggested_flag -eq 1 ]
    then
        echo "these recommended libraries were not found in your library path:$libraries_suggested"
    fi

    if [[ $tools_missing_flag -eq 1 || $codecs_missing_flag -eq 1 ]]
    then
        exit 1
    fi
}

function capitalize()
{
    echo "$@" | $sed_bin  's/ \(.\)/ \U\1/g' | $sed_bin  's/^\(.\)/\U\1/g' | $sed_bin "s/'n'\([a-z]\)/'N'\U\1/g" | $sed_bin "s/\( '. *\)/\U\1/g" | $sed_bin 's/\((.\)/\U\1/g'
}

function parse_cmdl_line()
{
    if [ $? -ne 0 ];
    then
        echo something went wrong with the command line parsing
        exit 1
    fi
    eval set -- "$cmdl_opt"

    while true;
    do
        case "$1" in
            -h|--help)
                echo "./lossless2lossy.sh [-hcygapkbqnmef] [--help|cover|year|genre|album|performer|comment|bitrate|cuefile|disc|discs|apple|fdk]"
                echo "    -h | --help prints this help"
                echo "    -c | --cover sets the cover file"
                echo "    -y | --year sets the year"
                echo "    -g | --genre sets the genre"
                echo "    -a | --album sets the album"
                echo "    -p | --performer sets the performer"
                echo "    -k | --comment sets the comment"
                echo "    -b | --bitrate sets the bitrate of encoding"
                echo "    -q | --cuefile sets the cuefile to use for track info"
                echo "    -d | --path sets the output path for the converted files"
                echo "    -n | --disc sets the number of disc"
                echo "    -m | --discs sets the total number of discs"
                echo "    -e | --apple if set it forces Apple's aac encoder"
                echo "    -f | --fdk if set it forces FDK aac encoder"
                shift
                exit 0
                ;;
            -c|--cover)
                cover=$2
	            shift
	            ;;
            -y|--year)
                year=$2
	            shift
	            ;;
            -g|--genre)
                genre=$2
                genre=$(capitalize $genre)
	            shift
	            ;;
            -a|--album)
                album=$2
                album=$(capitalize $album)
	            shift
	            ;;
            -p|--performer)
                album_artist=$2
                album_artist=$(capitalize $album_artist)
	            shift
	            ;;
            -k|--comment)
                comment=$2
	            shift
	            ;;
            -b|--bitrate)
                bitrate=$2
	            shift
	            ;;
            -q|--cuefile)
                cuefile=$2
	            shift
	            ;;
            -d|--path)
                outpath=$(echo $2/ | $sed_bin 's/\/\//\//')
	            shift
	            ;;
            -n|--disc)
                disc_idx=$2
	            shift
	            ;;
            -m|--discs)
                disc_tot=$2
	            shift
	            ;;
            -e|--apple)
                if [ -n "$fdk_aac_enable" ]
                then
                    echo either --apple or --fdk must be used
                    exit 1
                fi
                apple_aac_enable=1
	            ;;
            -f|--fdk)
                if [ -n "$apple_aac_enable" ]
                then
                    echo either --apple or --fdk must be used
                    exit 1
                fi
                fdk_aac_enable=1
	            ;;
            --) 
	            shift
	            break
	            ;;
        esac
        shift
    done
    return 0
}

function select_cuefile()
{
    if [ -z "$cuefile" ]
    then
        echo guessing cuefile to use...
        local cuefile_count=$(ls -1 *.cue 2> /dev/null | wc -l)
        if [ $cuefile_count -eq 1 ]
        then
            cuefile=$(ls *.cue)
            return 0
        elif [ $cuefile_count -gt 1 ]
        then
            echo please specify a cuefile
            exit 1
        else
            echo trying file-by-file mode...
            return 2
        fi
    else
        if [ ! -r "$cuefile" ]
        then
            echo the specified cuefile does not exist
            exit 1
        fi
        relative_path=$(dirname "$cuefile")/
    fi
    return 0
}

function get_album_tags()
{
    if [ $1 -eq 0 ]
    then
        cat "$cuefile" | $sed_bin 's/^REM //' > temp.cue

        n_tracks=$($cueprint_bin temp.cue 2> /dev/null -d '%N\n')
        if [ $n_tracks -lt 1 ]
        then
            echo "no track detected in cuefile"
            exit 1
        fi
        n_files=$($ack_bin '^FILE "' "$cuefile" | wc -l)
        if [ $n_tracks -lt 1 ]
        then
            echo "no file detected in cuefile"
            exit 1
        fi
        if [[ $n_files -gt 1 && $n_files -ne $n_tracks ]]
        then
            echo "the number of files in the cuesheet is not consistent with the number of tracks"
            exit 1
        fi

        if [ -z "$album_artist" ]
        then
            album_artist=$($cueprint_bin temp.cue 2>/dev/null -d '%P\n')
            album_artist=$(capitalize $album_artist)
        fi
        if [ -z "$album" ]
        then
            album=$($cueprint_bin temp.cue 2>/dev/null -d '%T\n')
            album=$(capitalize $album)
        fi
        if [ -z "$genre" ]
        then
            genre=$($cueprint_bin temp.cue 2>/dev/null -d '%G\n')
            genre=$(capitalize $genre)
        fi
        if [ -z "$year" ]
        then
            year=$($sed_bin -n 's/^DATE "\?\([0-9]*\)"\?[^0-9]*$/\1/p' temp.cue)
        fi
        if [ -z "$comment" ]
        then
            comment=$($sed_bin -n 's/^COMMENT "\(.*\)".*$/\1/p' temp.cue)
        fi
        if [ -f "temp.cue" ]
        then
            rm temp.cue
        fi
    elif [ $1 -eq 2 ]
    then
        local flac_count=$(ls -1 *.flac 2> /dev/null | wc -l | $sed_bin -n 's/\( *[0-9] *\)/\1/p')
        local m4a_count=$(ls -1 *.m4a 2> /dev/null | wc -l | $sed_bin -n 's/\( *[0-9] *\)/\1/p')
        local mp4_count=$(ls -1 *.mp4 2> /dev/null | wc -l | $sed_bin -n 's/\( *[0-9] *\)/\1/p')
        local ape_count=$(ls -1 *.ape 2> /dev/null | wc -l | $sed_bin -n 's/\( *[0-9] *\)/\1/p')
        file_format=flac
        n_files=$flac_count
        if [ $m4a_count -gt $flac_count ]
        then
            file_format=m4a
            n_files=$m4a_count
        fi
        if [ $mp4_count -gt $m4a_count ]
        then
            file_format=mp4
            n_files=$mp4_count
        fi
        if [ $ape_count -gt $mp4_count ]
        then
            file_format=ape
            n_files=$ape_count
        fi
        n_tracks=$n_files
        
        if [ $n_files -gt 0 ]
        then
            local infile=$(find . -iname "*.$file_format" | $sed_bin -n 1p)
            $ffmpeg_bin -i "$infile" -y -f ffmetadata temp.txt &> /dev/null
            performer=$($sed_bin -n 's/^ARTIST=\(.*\)$/\1/p' temp.txt)
            performer=$(capitalize $performer)
            album_artist=$performer
            album=$($sed_bin -n 's/^ALBUM=\(.*\)$/\1/p' temp.txt)
            album=$(capitalize $album)
            genre=$($sed_bin -n 's/^GENRE=\(.*\)$/\1/p' temp.txt)
            genre=$(capitalize $genre)
            year=$($sed_bin -n 's/^DATE=\([0-9][0-9]*\)$/\1/p' temp.txt)
            comment=$($sed_bin -n 's/^COMMENT=\(.*\)$/\1/p' temp.txt)

            if [ -f "temp.txt" ]
            then
                rm temp.txt
            fi
        else
            echo no file found
            exit 1
        fi
    else
	    echo unsupported mode
	exit 1
    fi

    if [ -z "$album_artist" ]
    then
        echo no album artist set by cuefile or file
    fi
    if [ -z "$album" ]
    then
        echo no album set by cuefile or file
    fi
    if [ -z "$genre" ]
    then
        echo no genre set by cuefile or file
    fi
    if [ -z "$year" ]
    then
        echo no year set by cuefile or file
    fi

    return 0
}

function select_encoder()
{
    if [[ -z $apple_aac_enable && -z $fdk_aac_enable ]]
    then
        apple_aac_enable=1
    fi
    if [ -n "$apple_aac_enable" ]
    then
        aac_tool=$afconvert_bin
        aac_tool_opt=$afconvert_opt
    elif [ -n "$fdk_aac_enable" ]
    then
        aac_tool=$fdkaac_bin
        aac_tool_opt=$fdkaac_opt
    else
        echo no encoder has been selected
        exit 1
    fi
    return 0
}

function tag_converted_files()
{
    if [ $use_atomicparsley -eq 1 ]
    then
        tag_cmdl='$atomicParsley_bin "$subdir$aac_file" --overWrite --tracknum "$track/$n_tracks"'
        tag_cmdl+=' --title "${title}"'
        tag_cmdl+=' --artist "$performer"'
        tag_cmdl+=' --album "$album"'
        tag_cmdl+=' --genre "$genre"'
        tag_cmdl+=' --year "$year"'
        tag_cmdl+=' --comment "$comment"'
        if [ $compilation -eq 1 ]
        then
            tag_cmdl+=' --albumArtist "$album_artist"'
        fi
        if [[ -n "$disc_idx" && -n "$disc_tot" ]]
        then
            tag_cmdl+=' --disk "$disc_idx/$disc_tot"'
        fi
        if [[ -n "$cover" && -f "$cover" ]]
        then
            tag_cmdl+=' --artwork "$cover"'
        fi
        eval $tag_cmdl &> /dev/null
    else
        $mp4box_bin -itags tracknum=$track/$n_tracks "$subdir$aac_file" &> /dev/null
        $mp4box_bin -itags name="${title}" "$subdir$aac_file" &> /dev/null
        $mp4box_bin -itags artist="$performer" "$subdir$aac_file" &> /dev/null
        $mp4box_bin -itags album="$album" "$subdir$aac_file" &> /dev/null
        $mp4box_bin -itags genre="$genre" "$subdir$aac_file" &> /dev/null
        $mp4box_bin -itags created="$year" "$subdir$aac_file" &> /dev/null
        $mp4box_bin -itags comment="$comment" "$subdir$aac_file" &> /dev/null
        if [ $compilation -eq 1 ]
        then
            $mp4box_bin -itags album_artist="$album_artist" "$subdir$aac_file" &> /dev/null
        fi
        if [[ -n "$disc_idx" && -n "$disc_tot" ]]
        then
            $mp4box_bin -itags disk=$disc_idx/$disc_tot "$subdir$aac_file" &> /dev/null
        fi
        if [[ -n "$cover" && -f "$cover" ]]
        then
            $mp4box_bin -itags cover="$cover" "$subdir$aac_file" &> /dev/null
        fi
    fi
    return 0
}

cmdl_opt=$(getopt -n "$0" -o hc:y:g:a:p:k:b:q:d:n:m:ef --long "help,cover:,year:,genre:,album:,performer:,comment:,bitrate:,cuefile:,path:,disc:,discs:,apple,fdk" -- "$@")

### BEGINNING OF SCRIPT ###

check_tools
parse_cmdl_line
select_cuefile; op_mode=$?
select_encoder
get_album_tags $op_mode
#print_debug

multiple_tracks=0
multiple_tracks_with_cuefile=0
if [ "$n_files" -eq "$n_tracks" ]
then
    multiple_tracks=1
    if [ $op_mode -eq 0 ]
    then
        multiple_tracks_with_cuefile=1
    fi
fi

subdir="$outpath$year - $album/"
if [[ -n "$disc_idx" && -n "$disc_tot" ]]
then
    subdir="$subdir/CD$disc_idx/"
fi
mkdir -p "$subdir"
declare -i track

if [[ "$n_files" -eq "1" && $op_mode -eq 0 ]]
then
    infile=$relative_path$($sed_bin -n 's/^FILE "\(.*\)".*$/\1/p' "$cuefile")
    if [ ! -f "$infile" ]
    then
        echo "the input file for the image does not exist (check the extension)"
        exit 1
    fi
    echo splitting the lossless image into wav tracks...
    echo
    $shntool_bin split -f "$cuefile" -d "$relative_path" -o wav -O always "$infile" &> /dev/null
    if [ -f "split-track00.wav" ]
    then
        rm "split-track00.wav"
    fi
fi

for (( track_idx=1; track_idx<=$n_tracks; track_idx++ ))
do
    if [ $op_mode -eq 0 ]
    then
        track=$track_idx
        title=$($cueprint_bin "$cuefile" 2>/dev/null -t '%t\n' -n $track)
        title=$(capitalize $title)
        if [[ -n $album_artist && $compilation -eq 0 ]]
        then
            performer="$album_artist"
        else
            performer=$($cueprint_bin "$cuefile" 2>/dev/null -t '%p\n' -n $track)
        fi
        performer=$(capitalize $performer)
        if [ -z "$title" ]
        then
            echo no title set by cuefile
        fi
    elif [ $op_mode -eq 2 ]
    then
        infile=$(find . -iname "*.$file_format" | $sed_bin -n ${track_idx}p)
        $ffmpeg_bin -i "$infile" -y -f ffmetadata temp.txt &> /dev/null
        title=$($sed_bin -n 's/^TITLE=\(.*\)$/\1/p' temp.txt)
        title=$(capitalize $title)
        track=$($sed_bin -n 's/^TRACK=\([0-9]\+\)$/\1/p' temp.txt | $sed_bin -n 's/^0\?//p')
        if [ "$track" == "0" ]
        then
            track=$($sed_bin -n 's/^track=\([0-9]\+\)$/\1/p' temp.txt | $sed_bin -n 's/^0\?//p')
        fi
        if [ -z "$track" ]
        then
	        echo "the track information for $infile is missing"
	        track=$track_idx
	    fi
        if [ -f "temp.txt" ]
        then
            rm temp.txt
        fi
        if [ -z "$title" ]
        then
            echo no title set by $file_format file
        fi
    else
	    echo unsupported mode
	exit 1
    fi
    
    aac_file="$(printf "%02d" ${track}) - $(echo ${title}.m4a | $sed_bin 's/?/-/' | $sed_bin 's/\//-/')"
    wav_file="split-track$(printf "%02d" ${track}).wav"

    if [ $multiple_tracks_with_cuefile -eq 1 ]
    then
        infile=$relative_path$($sed_bin -n 's/^FILE "\(.*\)".*$/\1/p' "$cuefile" | $sed_bin -n ${track}p)
        if [ ! -f "$infile" ]
        then
            echo "the input file for track # $track does not exist (check the extension)"
            exit 1
        fi
    fi

    if [ $multiple_tracks -eq 1 ]
    then
        echo "converting track # $track to wav format..."
        $ffmpeg_bin -y -i "$infile" "$relative_path$wav_file" &> /dev/null
    fi

    echo "converting track # $track to aac format..."
    eval $aac_tool $aac_tool_opt &> /dev/null

    echo "tagging track # $track"
    tag_converted_files

    if [ -f "$relative_path$wav_file" ]
    then
        rm "$relative_path$wav_file"
    fi
    echo
done
