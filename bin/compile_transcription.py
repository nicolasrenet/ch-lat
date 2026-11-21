#!/usr/bin/env python3

# nprenet@gmail.com
# 10/2026

"""
From a single transcription file where each abbreviated form is encoded as `[<what you read>|<what you see>]`
(eg. '[communitam|%munita%]'), generate 2 files, with expanded and abbreviated transcriptions, respectively. 

+ It enforces the assumption that annotations have been made mostly at word-level, even 
  though expansions ([<...>|) may contain transcriber-added spaces (_), that accordingly
  should not be used as separators between two annotations.
  Corollary: no `<what you read>|<what you see>` pair should contain a space.
+ Spaces are normalized.
+ Transcriber-added space markers ('_') can be part of expansions and are kept as such in the resulting output
+ All possible, unambiguous syntactic variations of annotations are handled:
  - [abc|cde], [abc|cde, abc|cde, abc|cde] →  'abc', 'cde'
  - [abc, [abc|, [abc|], abc| → 'abc', ''
  - cde], |cde], [|cde], |cde → '', 'cde'
  Note that some of these patterns don't have a well-defined meaning or are 
  problematic at best: '[abc|]' reads 'abc' out of nothing, '[|def]' reads 
  nothing from 'def' ('[$$$|def]' may be better), ...
+ Minimal dependencies: the file format can be anything where each transcripted document line is stored on its
  own line (eg. '"text": "..."' in JSON, or '<Unicode>...</Unicode>'). JSON is the default; PageXML is available
  as an option; additionally, a regexp pattern (with 1 group representing the transcription text portion of the
  line) may be passed for custom formats.

Input string:
    "sigilli [nostri|n%ri_[communitam|%munita%   [dedimus| quod| ape%det] Actu%]  anno |domi] Mo cco lxo ixo "

Expanded string:
    "sigilli nostri communitam dedimus quod anno Mo cco lxo ixo"

Abbreviated string:
    "sigilli n%ri %munita% ape%det Actu% anno domi Mo cco lxo ixo"


TODO:
    - compare with pre-GT files for
      + incomplete lines (bug in annotation tool)
      + removed uncertainty marks ($)
    - add processing description to "comment" key
"""

from pathlib import Path
import sys
import argparse
import re
import pytest
import logging

logger = logging.getLogger(__name__)

def normalize( input_line): 
    # removing parentheses (rare: ask Johannes)
    input_line = re.sub(r'[()]', '', input_line)
    # transcriber-added spaces (_) handled as regular spaces
    #return re.sub(r'[\s_]+', ' ', input_line.strip())
    return re.sub(r'[\s]+', ' ', input_line.strip())


pipe_separated_annotation_pattern = re.compile( r'\[?([^|\[\s]*)\|([^|\]\s]*)\]?-?' )

def compile_annotations( input_line, location_dict={} ):
    words = normalize( input_line ).split(' ')
    lefts, rights = [], []
    incompletes = []
    for w in words:#[(1 if skip_first else 0):]:
        try: 
            left, right = '', ''
            if w.find('|') >= 0:
                left, right = re.sub( pipe_separated_annotation_pattern, r'\1|\2', w).split('|')
            elif w[0]=='[':
                left, right = w[1:], ''
                incompletes.append( w )
            elif w[-1]==']':
                left, right = '', w[:-1]
                incompletes.append( w )
            else:
                left, right = w, w
        except ValueError as e:
            raise ValueError(f"{e} {w}")
        lefts.append( left )
        rights.append( right )
    if incompletes:
        logger.debug("Incomplete patterns" + (f" in {location_dict['filename']}:{location_dict['line_no']}" if location_dict else "") + f": {incompletes}" )
    return (' '.join( [ l for l in lefts if l ]), ' '.join([r for r in rights if r])) 
        

if __name__ == '__main__':
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("input_file", help="Input file; for standard input, indicate '-'.")
    parser.add_argument("--abbreviate", action='store_true', help="By default, the script generate both flavours of outputs; with this option, the abbreviated files are created, but their expanded counterpart is not, unless the '--expand' option is used.")
    parser.add_argument("--expand", action='store_true', help="By default, the script generate both flavours of outputs; with this option, the expanded files are created, but their abbreviated counterpart is not, unless the '--abbreviate' option is used.")
    parser.add_argument("--expanded_suffix", help="Suffix to be added to the expanded transcription before the '.json' suffix.", default=".exp")
    parser.add_argument("--abbreviated_suffix", help="Suffix to be added to the abbreviated transcription before the '.json' suffix.", default=".abr")
    parser.add_argument("--line_pattern", help="A custom line pattern to isolate relevant part of the transcription line.", default='')
    parser.add_argument("--input_format", help="File input format.", default="json")
    parser.add_argument("--standard_output", action='store_true', help="Use standard output only.") 
    parser.add_argument("--parallel", action='store_true', help="Generate a plain text, line-by-line parallel output of expanded and abbreviated transcriptions on 2 columns on the standard output, instead of two separate files (mostly for text processing purpose).")
    parser.add_argument("--plain", action='store_true', help="Generate a plain text version, with only the numbered transcription lines.")
    parser.add_argument("--width", type=int, default=0, help="Only with --parallel and --plain: limit column width to <width>.") 
    parser.add_argument("--overwrite_existing", action='store_true', help="Overwrite existing files with output.")
    parser.add_argument("--stats", action='store_true', default=False, help="Display basic statistics on transcriptions (lines, words, and characters.")
    parser.add_argument("--verbosity", choices=[0,1,2], help="Verbosity: 0=ERROR, 1=INFO, 2=DEBUG", type=int, default=1)

    args=parser.parse_args()

    logging.basicConfig(level=[logging.ERROR, logging.INFO, logging.DEBUG][args.verbosity])
    
    if args.input_file != '-' and not Path( args.input_file ).exists():
        logger.info(f'{args.input_file} does not exist. Abort.')
        sys.exit()

    # JSON default line pattern
    line_transcription_pattern = re.compile(r'(^\s*"text":\s+")([^"]+)(".*)$') if not args.line_pattern else re.compile( args.line_pattern )
    if args.input_format == 'page':
        line_transcription_pattern = re.compile( r'(^\s*<Unicode>)([^<]+)(</Unicode.*)$' )

    stats={"exp": {"lines": 0, "words": 0, "chars": 0}, "abr": {"lines": 0, "words": 0, "chars": 0} }

    def filter_line( line, stats ):
        transcription_match = line_transcription_pattern.match( line ) # whatever is a transcription in the input format (PageXML or JSON)
        if transcription_match:
            before = transcription_match.group(1)
            content = transcription_match.group(2)
            after = transcription_match.group(3)
            try:
                stats['exp']['lines']+=1
                stats['abr']['lines']+=1
                expanded_content, abbreviated_content = compile_annotations( content, {'filename': Path(args.input_file).name, 'line_no': stats['exp']['lines']} )
                for flavour, content in (("exp", expanded_content), ("abr", abbreviated_content)):
                    stats[flavour]['words']+= len(content.split(' '))
                    stats[flavour]['chars']+= len(list(content))
            except ValueError as e:
                logger.error(f"{e}: {args.input_file}:{stats[flavour]['lines']}")
                return tuple()
            if args.parallel:
                if args.width>0:
                    return (f"{stats[flavour]['lines']:2}. {expanded_content[:args.width]}...",f"{abbreviated_content[:args.width]}...")
                else:
                    return (f"{stats[flavour]['lines']:2}. {expanded_content}", f"{abbreviated_content}")
            elif args.plain:
                return ( 
                    "{:2}. {}\n".format( stats['exp']['lines'], expanded_content[:args.width] if args.width else expanded_content),
                    "{:2}. {}\n".format( stats['exp']['lines'], abbreviated_content[:args.width] if args.width else abbreviated_content))
            else:
                return( 
                    before + expanded_content + after + '\n',
                    before + abbreviated_content + after + '\n')
        # non-transcription input line are pass-through
        elif not (args.parallel or args.plain):
            return ( line, line )
        else:
            return ()

    expanded_lines, abbreviated_lines = [], []
    if args.input_file == '-':
        for line in sys.stdin:
            compiled_pair = filter_line( line, stats )
            if compiled_pair:
                exp_line, abbr_line =  compiled_pair
                expanded_lines.append( exp_line )
                abbreviated_lines.append( abbr_line )
    else:
        expanded_file_name = re.sub(r'\.[a-z]+\.([a-z]+)$', r'{}.\1'.format( args.expanded_suffix ), args.input_file )
        abbreviated_file_name = re.sub(r'\.[a-z]+\.([a-z]+)$', r'{}.\1'.format( args.abbreviated_suffix ), args.input_file )
        if args.plain:
            expanded_file_name = str(Path(expanded_file_name).with_suffix('.txt'))
            abbreviated_file_name = str(Path(abbreviated_file_name).with_suffix('.txt'))
        
        # just for logging purpose
        combined_name =  re.sub(r'\.[a-z]+\.([a-z]+)$', r'.{{{},{}}}.\1'.format( args.expanded_suffix[1:], args.abbreviated_suffix[1:] ), args.input_file )
        output_file_logstr = ''
        if not (args.abbreviate or args.expand) or (args.abbreviate and args.expand):
            output_file_logstr = combined_name
        elif args.expand:
            output_file_logstr = expanded_file_name
        else:
            output_file_logstr = abbreviated_file_name
        print(f"\n\n{args.input_file} →  {output_file_logstr if not args.standard_output else '-'}")

        with open( args.input_file ) as if_both:
            for line in if_both:
                compiled_pair = filter_line( line, stats )
                if compiled_pair:
                    exp_line, abbr_line =  compiled_pair
                    expanded_lines.append( exp_line )
                    abbreviated_lines.append( abbr_line )

    if not args.parallel:
        if args.expand or not (args.abbreviate or args.expand):
            if args.standard_output:
                for l in expanded_lines:
                    print(l, end='')
            else:
                if expanded_file_name.exists() and not args.overwrite_existing:
                    logger.warning(f"Output file {expanded_file_name} exists: skipping.")
                    sys.exit()
                with open(expanded_file_name, 'w') as of_exp:
                    for l in expanded_lines:
                        of_exp.write( l )

        if args.abbreviate or not (args.abbreviate or args.expand):
            if args.standard_output:
                for l in abbreviated_lines:
                    print(l, end='')
            else:
                if abbreviated_file_name.exists() and not args.overwrite_existing:
                    logger.warning(f"Output file {abbreviated_file_name} exists: skipping.")
                    sys.exit()
                with open( abbreviated_file_name, 'w') as of_abr:
                    for l in abbreviated_lines:
                        of_abr.write( l )
    else:
        #if args.standard_output:
        for exp_line, abbr_line in zip( expanded_lines, abbreviated_lines ):
            print(f"{exp_line}\t{abbr_line}")

    if args.stats:
        print("-------------------------------------")
        print("\t\tLines\tWords\tChars")
        print("Expanded\t{}\t{}\t{}".format(
                            stats['exp']['lines'],
                            stats['exp']['words'],
                            stats['exp']['chars']))
        print("Abbreviated\t{}\t{}\t{}".format(
                            stats['abr']['lines'],
                            stats['abr']['words'],
                            stats['abr']['chars']))
## Tests
                
@pytest.mark.parametrize("input_str, expected_left, expected_right",
                         [
                             ("sigilli [nostri|n%ri [communitam|%munitam   [dedimus|dedim% [quod|qd% apendet [Actum|Actu%  anno [domini|domi Mo cco lxo ixo ", "sigilli nostri communitam dedimus quod apendet Actum anno domini Mo cco lxo ixo", "sigilli n%ri %munitam dedim% qd% apendet Actu% anno domi Mo cco lxo ixo"),
                             ("westvalo in Stain [plebano|plbn%o [magistro|mg%is [Nycolao|Nycol% de Pyeska [Iur$$perico|Iur%pico Ortolf [Johannes|Johne% [Pernher|Pnh% [sacerdotibus|sac%dotib% [nostris|n%ris",
                              "westvalo in Stain plebano magistro Nycolao de Pyeska Iur$$perico Ortolf Johannes Pernher sacerdotibus nostris", 
                              "westvalo in Stain plbn%o mg%is Nycol% de Pyeska Iur%pico Ortolf Johne% Pnh% sac%dotib% n%ris"), 
                             ("[et|% Rogatis In [Cuius|Cui Rei [testimonio|testio%m plenius [presentes|p%ntes [litteras|lra%s [dedimus|dedim% [nostro|n%ro [pendenti|pend%nti",
                              "et Rogatis In Cuius Rei testimonio plenius presentes litteras dedimus nostro pendenti",
                              "% Rogatis In Cui Rei testio%m plenius p%ntes lra%s dedim% n%ro pend%nti"),
                             ("[communitam|%munita%]", "communitam", "%munita%"), # [abc|def]
                             ("[communitam|%munita%", "communitam", "%munita%"), # [abc|def
                             ("communitam|%munita%]", "communitam", "%munita%"), # abc|def]
                             ("communitam|%munita%", "communitam", "%munita%"), # abc|def
                             ('[et_inconvulsa|%ico%vulsa', 'et_inconvulsa', '%ico%vulsa'),])
def test_complete_patterns(input_str, expected_left, expected_right):

    left, right = compile_annotations( input_str )
    assert left == expected_left
    assert right== expected_right



@pytest.mark.parametrize("input_str, expected_left, expected_right",
                         [
                             ("sigilli [nostri_| [communitam|%munita%   [dedimus| quod| ape%det] Actu%]  anno |domi] Mo cco lxo ixo ", "sigilli nostri_ communitam dedimus quod anno Mo cco lxo ixo", "sigilli %munita% ape%det Actu% anno domi Mo cco lxo ixo"),
                             ("[communitam", "communitam", ""), # [exp
                             ("[communitam|", "communitam", ""), # [exp|
                             ("[communitam|]", "communitam", ""), # [exp|]
                             ("communitam|", "communitam", ""), # exp|
                             ("|%munita%", "", "%munita%"), # |exp
                             ("|%munita%]", "", "%munita%"), # |exp]
                             ("[|%munita%]", "", "%munita%"), # [|exp]
                             ("%munita%]", "", "%munita%"), # exp]
                         ])
def test_incomplete_patterns(input_str, expected_left, expected_right):

    left, right = compile_annotations( input_str )
    assert left == expected_left
    assert right== expected_right


@pytest.mark.parametrize("input_str, expected_left, expected_right",
                         [
                             ('[mines_gnadigen_herrn|msgh%en $ die jurisdiktion auf den beide', 'mines_gnadigen_herrn $ die jurisdiktion auf den beide', 'msgh%en $ die jurisdiktion auf den beide'),
                             ('sicut in [literis|l%ris suis [infrascriptis|infrasciptis lucidius pleniusque [declarabitur|declarabitr Diligenter [inspicerem|inspic%em ac [legerem|leg%em [ipsorumque|ip%or%_q% tenorem fideliter', 'sicut in literis suis infrascriptis lucidius pleniusque declarabitur Diligenter inspicerem ac legerem ipsorumque tenorem fideliter', 'sicut in l%ris suis infrasciptis lucidius pleniusque declarabitr Diligenter inspic%em ac leg%em ip%or%_q% tenorem fideliter'),
                             ])
def test_transcriber_spaces( input_str, expected_left, expected_right):

    left, right = compile_annotations( input_str )
    assert left == expected_left
    assert right== expected_right

