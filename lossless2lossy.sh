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
mp4box_bin=$(which mp4box)

# encoding options
bitrate="256000"
afconvert_opt='-v -d aac -f m4af -u pgcm 2 -q 127 -s 2 -b "$bitrate" --soundcheck-generate "$relative_path$wav_file" "$subdir$aac_file"'
fdkaac_opt='--profile 2 --bitrate-mode 0 --bitrate "$bitrate" --bandwidth 20000 --afterburner 1 -o "$subdir$aac_file" --ignorelength "$relative_path$wav_file"'

# tagging options
compilation=0
use_atomicparsley=0

function print_debug()
{
    echo $album
    echo $album_artist
    echo $year
    echo $genre
    echo $comment
    echo $bitrate
    echo $cuefile
    echo $cover
    if [ -n "$disc_idx" ]
    then
        echo $disc_idx
    fi
    if [ -n "$disc_tot" ]
    then
        echo $disc_tot
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
                echo "usage"
                echo "./flac2itunes.sh [-hcygapkbqnmef] [--help|cover|year|genre|album|performer|comment|bitrate|cuefile|disc|discs|apple|fdk]"
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
    cat "$cuefile" | $sed_bin 's/^REM //' >> temp.cue

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
        if [ -z "$album_artist" ]
        then
            echo no album artist set by cuefile
        fi
    fi
    if [ -z "$album" ]
    then
        album=$($cueprint_bin temp.cue 2>/dev/null -d '%T\n')
        album=$(capitalize $album)
        if [ -z "$album" ]
        then
            echo no album set by cuefile
        fi
    fi
    if [ -z "$genre" ]
    then
        genre=$($cueprint_bin temp.cue 2>/dev/null -d '%G\n')
        genre=$(capitalize $genre)
        if [ -z "$genre" ]
        then
            echo no genre set by cuefile
        fi
    fi
    if [ -z "$year" ]
    then
        year=$($sed_bin -n 's/^DATE \([0-9]*\)[^0-9]*$/\1/p' temp.cue)
        if [ -z "$year" ]
        then
            echo no year set by cuefile
        fi
    fi
    if [ -z "$comment" ]
    then
        comment=$($sed_bin -n 's/^COMMENT "\(.*\)".*$/\1/p' temp.cue)
    fi
    if [ -f "temp.cue" ]
    then
        rm temp.cue
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
    fi
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
}

cmdl_opt=$(getopt -n "$0" -o hc:y:g:a:p:k:b:q:d:n:m:ef --long "help,cover:,year:,genre:,album:,performer:,comment:,bitrate:,cuefile:,path:,disc:,discs:,apple,fdk" -- "$@")
    
parse_cmdl_line
#print_debug
select_cuefile; op_mode=$?
select_encoder

if [ $op_mode -eq 0 ]
then
    get_album_tags
    subdir="$outpath$year - $album/"
    if [[ -n "$disc_idx" && -n "$disc_tot" ]]
    then
        subdir="$subdir/CD$disc_idx/"
    fi
    mkdir -p "$subdir"
    declare -i track

    if [ "$n_files" -eq "1" ]
    then
        infile=$relative_path$($sed_bin -n 's/^FILE "\(.*\)".*$/\1/p' "$cuefile")
        if [ ! -f "$infile" ]
        then
            echo "the input file for the image does not exist (check the extension)"
        fi
        echo splitting the lossless image into wav tracks...
        echo
        $shntool_bin split -f "$cuefile" -d "$relative_path" -o wav -O always "$infile" &> /dev/null
    fi
    
    for (( track=1; track<=$n_tracks; track++ ))
    do
        title=$($cueprint_bin "$cuefile" 2>/dev/null -t '%t\n' -n $track)
        title=$(capitalize $title)
        if [[ -n $album_artist && $compilation -eq 0 ]]
        then
            performer="$album_artist"
        else
            performer=$($cueprint_bin "$cuefile" 2>/dev/null -t '%p\n' -n $track)
        fi
        performer=$(capitalize $performer)
	    aac_file="$(printf "%02d" ${track}) - $(echo ${title}.m4a | $sed_bin 's/?/-/' | $sed_bin 's/\//-/')"
        wav_file="split-track$(printf "%02d" ${track}).wav"
        if [ "$n_files" -eq "$n_tracks" ]
        then
            infile=$relative_path$($sed_bin -n 's/^FILE "\(.*\)".*$/\1/p' "$cuefile" | $sed_bin -n ${track}p)
            if [ ! -f "$infile" ]
            then
                echo "the input file for track # $track does not exist (check the extension)"
            fi
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
else
    echo this more is currently not implemented
fi
