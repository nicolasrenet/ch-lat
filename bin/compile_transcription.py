#!/usr/bin/env python3

# nprenet@gmail.com
# 10/2026

"""
From a single transcription file where each abbreviated form is encoded as [<what I read>|<what I see>] 
(eg. '[communitam|%munita%]'), generate 2 files, with expanded and abbreviated transcriptions, respectively. 

+ It enforces the assumption that annotations have been made at word-level: 
  any space (seen or added by the transcriber) is considered a separator, or,
  alternatively: no <what you read>|<what you see pair> should contain a space.
+ Spaces are normalized.
+ Transcriber-added space markers ('_') become ordinary white spaces in both output files.
+ All possible, unambiguous syntactic combinations of short and long versions of 
  <what you read>/<what you read> annotations are dealt with:
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
    return re.sub(r'[\s_]+', ' ', input_line.strip())


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
    parser.add_argument("input_file")
    parser.add_argument("--abbreviate", action='store_true', help="By default, the script generate both flavours of outputs; with this option, the abbreviated files are created, but their expanded counterpart is not, unless the '--expand' option is used.")
    parser.add_argument("--expand", action='store_true', help="By default, the script generate both flavours of outputs; with this option, the expanded files are created, but their abbreviated counterpart is not, unless the '--abbreviate' option is used.")
    parser.add_argument("--expanded_suffix", help="Suffix to be added to the expanded transcription before the '.json' suffix.", default=".exp")
    parser.add_argument("--abbreviated_suffix", help="Suffix to be added to the abbreviated transcription before the '.json' suffix.", default=".abr")
    parser.add_argument("--line_pattern", help="A custom line pattern to isolate relevant part of the transcription line.", default=r'(^\s*"text":\s+")([^"]+)(".*)$')
    parser.add_argument("--input_format", help="File input format.", default="json")
    parser.add_argument("--verbosity", choices=[0,1,2], help="Verbosity: 0=ERROR, 1=INFO, 2=DEBUG", type=int, default=1)

    args=parser.parse_args()

    logging.basicConfig(level=[logging.ERROR, logging.INFO, logging.DEBUG][args.verbosity])
    
    if not Path( args.input_file ).exists():
        logger.info(f'{args.input_file} does not exist. Abort.')
        sys.exit()

    line_transcription_pattern = re.compile( args.line_pattern ) if not args.input_format=='xml' else re.compile( r'(^\s*<Unicode>)([^<]+)(<Unicode.*)$' )

    expanded_file_name = re.sub(r'\.[a-z]+\.([a-z]+)$', r'{}.\1'.format( args.expanded_suffix ), args.input_file )
    abbreviated_file_name = re.sub(r'\.[a-z]+\.([a-z]+)$', r'{}.\1'.format( args.abbreviated_suffix ), args.input_file )
    
    # just for logging purpose
    combined_name =  re.sub(r'\.[a-z]+\.([a-z]+)$', r'.{{{},{}}}.\1'.format( args.expanded_suffix[1:], args.abbreviated_suffix[1:] ), args.input_file )
    output_file_logstr = ''
    if not (args.abbreviate or args.expand) or (args.abbreviate and args.expand):
        output_file_logstr = combined_name
    elif args.expand:
        output_file_logstr = expanded_file_name
    else:
        output_file_logstr = abbreviated_file_name
    logger.info(f"{args.input_file} → {output_file_logstr}")

    with open( args.input_file ) as if_both:
        text_line_count = 0
        expanded_lines, abbreviated_lines = [], []
        for line in if_both:
            transcription_match = line_transcription_pattern.match( line )
            if transcription_match:
                before = transcription_match.group(1)
                content = transcription_match.group(2)
                after = transcription_match.group(3)
                text_line_count += 1
                try:
                    expanded_content, abbreviated_content = compile_annotations( content, {'filename': Path(args.input_file).name, 'line_no': text_line_count} )
                except ValueError as e:
                    logger.error(f"{e}: {args.input_file}:{text_line_count}")
                    continue
                expanded_lines.append( before + expanded_content + after + '\n') 
                abbreviated_lines.append( before + abbreviated_content + after + '\n')
            else:
                expanded_lines.append( line )
                abbreviated_lines.append( line )

        if args.expand or not (args.abbreviate or args.expand):
            with open(expanded_file_name, 'w') as of_exp:
                for l in expanded_lines:
                    of_exp.write( l )

        if args.abbreviate or not (args.abbreviate or args.expand):
            with open( abbreviated_file_name, 'w') as of_abr:
                for l in abbreviated_lines:
                    of_abr.write( l )

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
                             ('[et_inconvulsa|%ico%vulsa', 'et inconvulsa', '%ico%vulsa'),])
def test_complete_patterns(input_str, expected_left, expected_right):

    left, right = compile_annotations( input_str )
    assert left == expected_left
    assert right== expected_right



@pytest.mark.parametrize("input_str, expected_left, expected_right",
                         [
                             ("sigilli [nostri_[communitam|%munita%   [dedimus| quod| ape%det] Actu%]  anno |domi] Mo cco lxo ixo ", "sigilli nostri communitam dedimus quod anno Mo cco lxo ixo", "sigilli %munita% ape%det Actu% anno domi Mo cco lxo ixo"),
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



