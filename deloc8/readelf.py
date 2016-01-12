"""
Functions for processing ELF files
"""
import os.path
import logging
from typing import Iterator, Tuple, List

from elftools.common.exceptions import ELFError
from elftools.elf.dynamic import DynamicSection
from elftools.elf.elffile import ELFFile

from .linkertools import parse_ld_path


log = logging.getLogger(__name__)


def elf_file_filter(paths: Iterator[str]) -> Iterator[Tuple[str, ELFFile]]:
    for path in paths:
        if path.endswith('.py'):
            continue
        else:
            try:
                with open(path, 'rb') as f:
                    candidate = ELFFile(f)
                    yield path, candidate
            except ELFError:
                # not an elf file
                continue


def elf_inspect_dynamic(fn, elf) -> Tuple[List[str], List[str]]:
    """Read DT_NEEDED and DT_RPATH/DT_RUNPATH from dynamic section of an ELF file
    """
    section = elf.get_section_by_name(b'.dynamic')

    dt_needed = []
    dt_rpath = []
    dt_runpath = []

    if section is not None:
        for tag in section.iter_tags():
            if tag.entry.d_tag == 'DT_NEEDED':
                dt_needed.append(tag.needed.decode('utf-8'))
            elif tag.entry.d_tag == 'DT_RPATH':
                dt_rpath.extend(parse_ld_path(tag.rpath.decode('utf-8')))
            elif tag.entry.d_tag == 'DT_RUNPATH':
                dt_runpath.extend(parse_ld_path(tag.runpath.decode('utf-8')))

    def replace(p: str) -> str:
        return p.replace('$ORIGIN', os.path.dirname(fn))

    if dt_runpath:
        # ignore rpath if runpath is given
        return dt_needed, [replace(p) for p in dt_runpath]
    return dt_needed, [replace(p) for p in dt_rpath]


def elf_find_versioned_symbols(elf: ELFFile) -> Iterator[Tuple[str, str]]:
    section = elf.get_section_by_name(b'.gnu.version_r')
    for verneed, verneed_iter in section.iter_versions():
        for vernaux in verneed_iter:
            yield (verneed.name.decode('utf-8'),
                   vernaux.name.decode('utf-8'))
