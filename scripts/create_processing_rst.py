import argparse
import os
import re
import subprocess
from os import makedirs
from os.path import join
from pathlib import Path
from typing import List, Union

from qgis.core import QgsProcessingAlgorithm, QgsProcessingDestinationParameter, QgsProcessingParameterDefinition

import enmapbox
from enmapbox.algorithmprovider import EnMAPBoxProcessingProvider
from enmapbox.qgispluginsupport.qps.utils import file_search
from enmapbox.testing import start_app
from enmapboxprocessing.enmapalgorithm import EnMAPProcessingAlgorithm, Group
from enmapboxprocessing.glossary import injectGlossaryLinks

rootCodeRepo = Path(__file__).parent.parent

if 'PATH_DOCU_REPO' in os.environ:
    rootDocRepo = Path(os.environ['PATH_DOCU_REPO'])
else:
    rootDocRepo = rootCodeRepo.parent / 'enmap-box-documentation'

    os.makedirs(rootDocRepo, exist_ok=True)
assert rootDocRepo.is_dir()

dryRun = False  # a fast way to check if all parameters are documented

# environment to run qgis_process from python shell command
QGIS_PROCESS_ENV = os.environ.copy()
for k in ['QGIS_CUSTOM_CONFIG_PATH', 'QT3D_RENDERER']:
    if k in QGIS_PROCESS_ENV:
        QGIS_PROCESS_ENV.pop(k)


def read_existing_rsts(rootRst: Union[str, Path]):
    rootRst = Path(rootRst)

    infos = dict()
    if not rootRst.is_dir():
        return infos

    for p in file_search(rootRst, '*.rst', recursive=True):
        with open(p, 'r') as f:
            rst_test = f.read()

            infos[rootRst.as_posix()] = rst_test
    return infos


def write_and_update(file, text):
    file = Path(file)
    # todo: if file exists, keep none-autogenerated parts

    if isinstance(text, list):
        text = '\n'.join(text)

    with open(file, 'w', encoding='utf-8') as f:
        f.write(text)

    print(f'Created {file}')


def generateAlgorithmRSTs(rootRst, algorithms: List[QgsProcessingAlgorithm]) -> List[str]:
    rootRst = Path(rootRst)
    if isinstance(algorithms, QgsProcessingAlgorithm):
        algorithms = [algorithms]

    for alg in algorithms:

        text = v3(alg)

        afilename = alg.name()
        for c in r'/() ':
            afilename = afilename.replace(c, '_')

        filename = rootRst / groupFolderName(alg.group()) / '{}.rst'.format(afilename)
        write_and_update(filename, text)


def groupFolderName(group: str) -> str:
    name = group.lower()
    for c in ' ,*':
        name = name.replace(c, '_')
    return name


def generateGroupRSTs(rootRst, algorithms: List[QgsProcessingAlgorithm]) -> List[str]:
    rootRst = Path(rootRst)

    groups = set([a.group() for a in algorithms])

    index_files: List[str] = []
    for group in groups:
        # create group folder
        groupFolder = rootRst / groupFolderName(group)
        makedirs(groupFolder, exist_ok=True)

        # create group index.rst
        # create group index.rst
        text = [
            f'.. _{group}:\n',
            f'{group}',
            f'{'=' * len(group)}',
            '.. toctree::',
            '   :maxdepth: 0',
            '   :glob:\n',
            '   *\n'
        ]

        filename = groupFolder / 'index.rst'
        write_and_update(filename, '\n'.join(text))
        index_files.append(f'{groupFolder.name}/{filename.name}')

    # write processing_algorithsm.rst
    textProcessingAlgorithmsRst = [
        'Processing Algorithms',
        '*********************',
        '',
        '.. toctree::',
        '    :maxdepth: 1\n'
    ]
    textProcessingAlgorithmsRst.extend([f'    {f}' for f in index_files])

    filename = rootRst / 'processing_algorithms.rst'
    write_and_update(filename, '\n'.join(textProcessingAlgorithmsRst))

    return index_files


def generateRST(rootRst=None,
                algorithmIds: List[str] = None
                ):
    # create folder
    print(rootCodeRepo)

    if rootRst is None:
        print(rootDocRepo)
        rootRst = join(rootDocRepo, 'source', 'usr_section', 'usr_manual', 'processing_algorithms')

    print(rootRst)

    assert isinstance(EnMAPBoxProcessingProvider.instance(), EnMAPBoxProcessingProvider)
    makedirs(rootRst, exist_ok=True)

    # filter algorithms
    algs: List[QgsProcessingAlgorithm] = []
    for alg in EnMAPBoxProcessingProvider.instance().algorithms():
        if Group.Experimental.name in alg.group():
            raise RuntimeError('Remove experimental algorithms from final release!')
        algs.append(alg)

    # optional: filter algorithms (e.g. for testing)
    if algorithmIds:
        algs = [a for a in algs if a.id() in algorithmIds or a.name() in algorithmIds]

    # create group folders, <group>/index.rst and processing_algorithms.rst

    generateGroupRSTs(rootRst, algs)
    generateAlgorithmRSTs(rootRst, algs)

    s = ""


def wrapAutoGenerated(rst_text: str, section: str) -> str:
    """Wraps autogenerated content with start and end markers"""
    return f"..\n  ## AUTOGENERATED {section} START\n\n{rst_text}\n\n..\n  ## AUTOGENERATED {section} END\n\n"


def v3(alg: QgsProcessingAlgorithm):
    if isinstance(alg, EnMAPProcessingAlgorithm):
        helpParameters = {k: v for k, v in alg.helpParameters()}
    else:
        helpParameters = dict()

    # Title Section
    title = alg.displayName()
    dotline = '*' * len(title)
    title_text = f".. _{title}:\n\n{dotline}\n{title}\n{dotline}\n"
    title_text = utilsConvertHtmlLinksToRstLinks(title_text)  # Convert any HTML links
    text = wrapAutoGenerated(title_text, "TITLE")

    # Description Section
    description_text = injectGlossaryLinks(alg.shortDescription())
    description_text = utilsConvertHtmlLinksToRstLinks(description_text)  # Convert HTML links
    text += wrapAutoGenerated(description_text, "DESCRIPTION")

    # Parameters Section
    param_text = ''
    outputsHeadingCreated = False
    for pd in alg.parameterDefinitions():
        assert isinstance(pd, QgsProcessingParameterDefinition)

        pdhelp = helpParameters.get(pd.description(), 'undocumented')
        if pdhelp == '':
            continue
        if pdhelp == 'undocumented':
            assert 0, pd.description()

        if not outputsHeadingCreated and isinstance(pd, QgsProcessingDestinationParameter):
            param_text += '**Outputs**\n\n'
            outputsHeadingCreated = True

        param_text += f'\n:guilabel:`{pd.description()}` [{pd.type()}]\n'
        pdhelp = injectGlossaryLinks(pdhelp)
        pdhelp = utilsConvertHtmlLinksToRstLinks(pdhelp)  # Convert HTML links in help text
        for line in pdhelp.split('\n'):
            param_text += f'    {line}\n'

        if pd.defaultValue() is not None:
            if isinstance(pd.defaultValue(), str) and '\n' in pd.defaultValue():
                param_text += '    Default::\n\n'
                for line in pd.defaultValue().split('\n'):
                    param_text += f'        {line}\n'
            else:
                param_text += f'    Default: *{pd.defaultValue()}*\n\n'

    text += wrapAutoGenerated(param_text, "PARAMETERS")

    # Command-line usage
    helptext = qgis_process_help(alg)
    helptext = helptext[helptext.find('----------------\nArguments\n----------------'):]
    helptext = utilsConvertHtmlLinksToRstLinks(helptext)  # Convert HTML links in usage text

    usage_text = f"**Command-line usage**\n\n``>qgis_process help {alg.id()}``::\n\n"
    usage_text += '\n'.join([f'    {line}' for line in helptext.splitlines()])

    text += wrapAutoGenerated(usage_text, "COMMAND USAGE")

    return text


def qgis_process_help(algorithm: QgsProcessingAlgorithm) -> str:
    result = subprocess.run(['qgis_process', 'help', algorithm.id()],
                            env=QGIS_PROCESS_ENV,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE
                            )
    assert result.returncode == 0
    helptext = result.stdout.decode('cp1252')
    return helptext


def utilsConvertHtmlLinksToRstLinks(text: str) -> str:
    """Convert all HTML-style links in the text to RST-style links."""
    links = utilsFindHtmlWeblinks(text)  # Find all HTML links in the text
    for html_link in links:
        rst_link = utilsHtmlWeblinkToRstWeblink(html_link)
        text = text.replace(html_link, rst_link)
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
    parser = argparse.ArgumentParser(description='Generates the documentation for EnMAPBox processing algorithms ',
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-r', '--rst_root',
                        required=False,
                        default=rootDocRepo.as_posix(),
                        help=f'Root folder to write the RST files. Defaults to {rootDocRepo}')

    parser.add_argument('-a', '--algs',
                        required=False,
                        nargs='*',
                        default=None,
                        help='List of algorithms ids to generate the documentation for')

    args = parser.parse_args()

    rootRst = Path(args.rst_root)
    if not rootRst.is_absolute():
        rootRst = rootCodeRepo / rootRst

    algs = args.algs

    start_app()
    enmapbox.initAll()
    generateRST(rootRst, algs)
