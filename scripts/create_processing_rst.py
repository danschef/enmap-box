import os
import re
import subprocess
from os import makedirs
from os.path import abspath, join, dirname, exists, basename
from pathlib import Path
from shutil import rmtree
from typing import List

import enmapbox
from enmapboxprocessing.algorithm.algorithms import algorithms
from enmapboxprocessing.enmapalgorithm import EnMAPProcessingAlgorithm, Group
from enmapboxprocessing.glossary import injectGlossaryLinks
from qgis.core import QgsProcessingParameterDefinition, QgsProcessingDestinationParameter

rootCodeRepo = Path(__file__).parent.parent

if 'PATH_DOCU_REPO' in os.environ:
    rootDocRepo = Path(os.environ['PATH_DOCU_REPO'])
else:
    rootDocRepo = rootCodeRepo.parent / 'enmap-box-documentation'

    os.makedirs(rootDocRepo, exist_ok=True)
assert rootDocRepo.is_dir()

dryRun = False  # a fast way to check if all parameters are documented


def generateRST():
    # create folder
    print(rootCodeRepo)
    print(rootDocRepo)

    rootRst = join(rootDocRepo, 'source', 'usr_section', 'usr_manual', 'processing_algorithms')
    print(rootRst)

    if exists(rootRst):
        print('Delete root folder')
        rmtree(rootRst)
    makedirs(rootRst)

    groups = dict()

    nalg = 0
    algs = algorithms()
    for alg in algs:
        # print(alg.displayName())
        if Group.Experimental.name in alg.group():
            raise RuntimeError('Remove experimental algorithms from final release!')
        if alg.group() not in groups:
            groups[alg.group()] = dict()
        groups[alg.group()][alg.displayName()] = alg
        nalg += 1

    print(f'Found {nalg} algorithms.')

    textProcessingAlgorithmsRst = '''Processing Algorithms
*********************

.. toctree::
    :maxdepth: 1

'''

    for gkey in sorted(groups.keys()):

        # create group folder
        groupId = gkey.lower()
        for c in ' ,*':
            groupId = groupId.replace(c, '_')
        groupFolder = join(rootRst, groupId)
        makedirs(groupFolder)

        textProcessingAlgorithmsRst += '\n    {}/index.rst'.format(basename(groupFolder))

        # create group index.rst
        text = '''.. _{}:\n\n{}
{}

.. toctree::
   :maxdepth: 0
   :glob:

   *
'''.format(gkey, gkey, '=' * len(gkey))
        filename = join(groupFolder, 'index.rst')
        with open(filename, mode='w', encoding='utf-8') as f:
            f.write(text)

        for akey in groups[gkey]:

            algoId = akey.lower()
            for c in [' ']:
                algoId = algoId.replace(c, '_')

            text = '''.. _{}:

{}
{}


'''.format(akey, '*' * len(akey), akey)

            alg = groups[gkey][akey]
            print(alg)

            if isinstance(alg, EnMAPProcessingAlgorithm):
                alg.initAlgorithm()
                text = v3(alg, text, groupFolder, algoId)
            else:
                print(f'skip {alg}')
                continue

            filename = join(groupFolder, '{}.rst'.format(algoId))
            for c in r'/()':
                filename = filename.replace(c, '_')
            with open(filename, mode='w', encoding='utf-8') as f:
                f.write(text)

    filename = join(rootRst, 'processing_algorithms.rst')
    with open(filename, mode='w', encoding='utf-8') as f:
        f.write(textProcessingAlgorithmsRst)
    print('created RST file: ', filename)


def v3(alg: EnMAPProcessingAlgorithm, text, groupFolder, algoId):
    try:
        helpParameters = {k: v for k, v in alg.helpParameters()}
    except Exception:
        assert 0

    # Clear autogenerated title, removing any manual _Build 3D Cube before this block
    title = alg.displayName()
    title_underline = '*' * len(title)  # This will ensure proper length of the underline

    # Generate title with proper format and markers
    text = '''.. ## AUTOGENERATED TITLE START ##
.. _{}:

{}
{}
.. ## AUTOGENERATED TITLE END ##
'''.format(title, title, title_underline)

    text += '\nHere I can add my manual defined rst code\n\n'

    # Autogenerated Description
    text += '''.. ## AUTOGENERATED DESCRIPTION START ##
{}
.. ## AUTOGENERATED DESCRIPTION END ##
'''.format(injectGlossaryLinks(alg.shortDescription()))

    # Manual content after description
    text += '\nHere I can add more manual defined rst code\n\n'

    # Autogenerated Parameters Section
    text += '\n**Parameters**\n\nHere I can add more manual content for Parameters.\n\n'
    text += '''.. ## AUTOGENERATED PARAMETERS START ##
'''

    outputsHeadingCreated = False
    for pd in alg.parameterDefinitions():
        assert isinstance(pd, QgsProcessingParameterDefinition)

        pdhelp = helpParameters.get(pd.description(), 'undocumented')
        if pdhelp == '':
            continue
        if pdhelp == 'undocumented':
            assert 0, pd.description()

        if not outputsHeadingCreated and isinstance(pd, QgsProcessingDestinationParameter):
            text += '**Outputs**\n\n'
            outputsHeadingCreated = True

        text += '\n:guilabel:`{}` [{}]\n'.format(pd.description(), pd.type())

        pdhelp = injectGlossaryLinks(pdhelp)

        for line in pdhelp.split('\n'):
            text += '    {}\n'.format(line)

        text += '\n'

        if pd.defaultValue() is not None:
            if isinstance(pd.defaultValue(), str) and '\n' in pd.defaultValue():
                text += '    Default::\n\n'
                for line in pd.defaultValue().split('\n'):
                    text += '        {}\n'.format(line)
            else:
                text += '    Default: *{}*\n\n'.format(pd.defaultValue())

    text += '''.. ## AUTOGENERATED PARAMETERS END ##
'''

    # Allow manual addition after Parameters section
    text += '\nHere I can add even more manual defined rst code\n\n'

    # Add command-line usage
    algoId = 'enmapbox:' + alg.name()
    result = subprocess.run(['qgis_process', 'help', algoId], stdout=subprocess.PIPE)
    helptext = result.stdout.decode('cp1252')
    helptext = helptext[helptext.find('----------------\nArguments\n----------------'):]

    # Autogenerated Command-line Usage
    text += '''.. ## AUTOGENERATED COMMAND USAGE START ##
**Command-line usage**

``>qgis_process help {}``::

{}
.. ## AUTOGENERATED COMMAND USAGE END ##
'''.format(algoId, '\n'.join(['    ' + line for line in helptext.splitlines()]))

    return text


def utilsFindHtmlWeblinks(text) -> List[str]:
    match_: re.Match
    starts = [match_.start() for match_ in re.finditer('<a href="', text)]
    ends = [match_.start() + 4 for match_ in re.finditer('</a>', text)]
    assert len(starts) == len(ends)
    links = [text[start:end] for start, end in zip(starts, ends)]
    return links


def utilsHtmlWeblinkToRstWeblink(htmlText: str) -> str:
    assert htmlText.startswith('<a href="'), htmlText
    assert htmlText.endswith('</a>'), htmlText
    link, name = htmlText[9:-4].split('">')
    rstText = f'`{name} <{link}>`_'
    return rstText


if __name__ == '__main__':
    generateRST()
