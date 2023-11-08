"""
@package pydoctrinediagrams

Builds svg diagram for database structure.
"""
import os
import sys
import logging
import pydot
import argparse
from pydoctrinediagrams.entitynode import EntityNode

_p = argparse.ArgumentParser(description='Generates database diagram.')
_p.add_argument(
    '-i',
    '--input',
    help='Glob pattern for database metadata yml files.',
    type=str,
    default='./*.yml'
)
_p.add_argument(
    '-t',
    '--title',
    help='Diagram title.',
    type=str,
    default='Entities'
)
_p.add_argument(
    '-o',
    '--output',
    help='Path to output file.',
    type=str,
    default='./diagram.svg'
)
_a = _p.parse_args()
_entities = EntityNode.load_entities(_a.input)

_graph = pydot.Dot(
    'entities',
    labelloc='t',
    label=_a.title,
    graph_type='digraph',
    bgcolor='white',
    fontcolor='black'
)
for _entity in _entities:
    _entities[_entity].create_node(_graph)
for _entity in _entities:
    _entities[_entity].create_edges(_graph, _entities)
_graph.write_svg(_a.output)
