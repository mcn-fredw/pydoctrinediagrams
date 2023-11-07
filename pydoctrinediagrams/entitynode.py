"""
@package pydoctrinediagrams

Builds svg diagram for database structure.
"""
from typing import NoReturn
import os
import sys
import logging
import pydot
from ruamel.yaml import YAML, yaml_object
import glob

class EntityNode(object):

    COLORS = [
        'black', 'coral4', 'aquamarine4', 'fuchsia',
        'darkgreen', 'darkorchid3', 'dimgrey', 'darkorange3',
        'darkslateblue', 'goldenrod4', 'deepskyblue4', 'darkmagenta',
        'cyan2', 'blue2', 'darkseagreen3', 'firebrick4', 'green4'
    ]
    COLOR_INDEX = 0

    @staticmethod
    def next_color() -> str:
        _color = EntityNode.COLORS[EntityNode.COLOR_INDEX]
        EntityNode.COLOR_INDEX += 1
        if len(EntityNode.COLORS) == EntityNode.COLOR_INDEX:
            EntityNode.COLOR_INDEX = 0
        return _color

    @classmethod
    def load_entities(cls, inglob) -> list:
        yaml = YAML()
        # load entities from files
        _map = dict()
        _files = glob.glob(inglob)
        for _f in _files:
            with open(_f) as yf:
                _entity = yaml.load(yf)
                for _fqcn in _entity:
                    if 'entity' == _entity[_fqcn]['type']:
                        _map[_fqcn] = cls(_fqcn, _entity[_fqcn])
        # populate entity fields
        _keys = list(_map.keys())
        for _fqcn in _keys:
            _map[_fqcn].populate_fields(_map)
        _keys = list(_map.keys())
        for _fqcn in _keys:
            _map[_fqcn].assign_ids()
        return _map
        
    def __init__(
        self,
        fqcn: str,
        meta: dict,
        *pargs: list,
        **dargs: dict
    ) -> NoReturn:
        super(EntityNode, self).__init__(*pargs, **dargs)
        self.fqcn = fqcn
        self.meta = meta
        self.fields = dict()
        self.color = EntityNode.next_color()

    def populate_fields(self, master: dict) -> NoReturn:
        # strait up fields
        for _k in ['id', 'fields']:
            if _k not in self.meta:
                print(f' no {_k} found in {self.fqcn}')
                continue
            for _f in self.meta[_k]:
                if _f not in self.fields:
                    self.fields[_f] = {'t': 'unknown'}
                if 'type' in self.meta[_k][_f]:
                    self.fields[_f]['t'] = self.meta[_k][_f]['type']
        # relational fields
        _rMap = {
            'oneToOne': self.one_to_one,
            'oneToMany': self.one_to_many,
            'manyToOne': self.many_to_one,
            'manyToMany': self.many_to_many
        }
        for _k in _rMap:
            if _k not in self.meta:
                continue
            for _v in self.meta[_k]:
                _rMap[_k](_v, self.meta[_k][_v], master)
        pass
    
    def one_to_one(self, field: str, relation: dict, master: dict) -> NoReturn:
        # mappedBy says what points to my key (edge tail)
        # inversedBy tells who's id we point to (edge head)
        _f = f"${field}"
        _target_key = relation['targetEntity']
        _re = master[_target_key]
        self.fields[_f] = {
            't':  _target_key.split("\\")[-1],
            're': _target_key
        }
        _mb = relation['mappedBy'] if 'mappedBy' in relation else None
        if _mb:
            _tf = f"${_mb}"
            if _tf not in _re.fields:
                _re.fields[_tf] = {
                    't': self.fqcn.split("\\")[-1],
                    're': self.fqcn
                }
            return
        _ib = relation['inversedBy'] if 'inversedBy' in relation else None
        if _ib:
            _tf = f"${_ib}"
            if _tf not in _re.fields:
                _re.fields[_tf] = {
                    't': self.fqcn.split("\\")[-1],
                    're': self.fqcn
                }
            if 'joinColumns' in relation:
                for _jc in relation['joinColumns']:
                    _re.fields[_tf]['rc'] = relation['joinColumns'][_jc]['referencedColumnName']
        pass

    def one_to_many(self, field: str, relation: dict, master: dict) -> NoReturn:
        # mappedBy says what points to my key (edge tail)
        _f = f"${field}"
        _target_key = relation['targetEntity']
        _re = master[_target_key]
        self.fields[_f] = {
            't':  _target_key.split("\\")[-1],
            're': _target_key
        }
        _mb = relation['mappedBy'] if 'mappedBy' in relation else None
        if _mb:
            _tf = f"${_mb}"
            if _tf not in _re.fields:
                _re.fields[_tf] = {
                    't': self.fqcn.split("\\")[-1],
                    're': self.fqcn
                }
        pass

    def many_to_one(self, field: str, relation: dict, master: dict) -> NoReturn:
        # inversedBy tells who's id we point to (edge head)
        _f = f"${field}"
        _target_key = relation['targetEntity']
        _re = master[_target_key]
        self.fields[_f] = {
            't':  _target_key.split("\\")[-1],
            're': _target_key
        }
        _ib = relation['inversedBy'] if 'inversedBy' in relation else None
        if _ib and 'joinColumns' in relation:
            for _jc in relation['joinColumns']:
                self.fields[_f]['rc'] = relation['joinColumns'][_jc]['referencedColumnName']
        if _ib:
            _tf = f"${_ib}"
            if _tf not in _re.fields:
                _re.fields[_tf] = {
                    't': self.fqcn.split("\\")[-1],
                    're': self.fqcn
                }
        pass

    def many_to_many(self, field: str, relation: dict, master: dict) -> NoReturn:
        # joinTable gives the intersect info
        _join = relation['joinTable']
        if 'name' not in _join:
            # no point in processing an empty join
            return
        _target_key = relation['targetEntity']
        _f = f"${field}"
        _re = master[_target_key]
        _intersect = EntityNode(_join['name'], {'table': _join['name']})
        for _jc in _join['joinColumns']:
            _intersect.fields[_jc['name']] = {
                't': self.fields[_jc['referencedColumnName']]['t'],
                're': self.fqcn,
                'rc': _jc['referencedColumnName']
            }
        for _jc in _join['inverseJoinColumns']:
            _intersect.fields[_jc['name']] = {
                't': _re.fields[_jc['referencedColumnName']]['t'],
                're': _re.fqcn,
                'rc': _jc['referencedColumnName']
            }
        master[_intersect.fqcn] = _intersect

    def assign_ids(self) -> NoReturn:
        _n = 1
        self.fields = dict(sorted(self.fields.items()))
        for _f in self.fields:
            self.fields[_f]['fid'] = _n
            _n += 1
        pass

    def create_label(self) -> str:
        _label = list()
        _fields = list()
        _label.append("{")
        _fields.append(f"<f0> {self.meta['table']}")
        for _f in self.fields:
            _fields.append(f"<f{self.fields[_f]['fid']}> {_f}  ({self.fields[_f]['t']})\l")
        _label.append('| '.join(_fields))
        _label.append('}')
        return ''.join(_label)

    def create_node(self, graph: pydot.Dot) -> NoReturn:
        _n = pydot.Node(
            self.meta['table'],
            label=self.create_label(),
            shape='Mrecord',
            style='filled',
            nojustify=False,
            fillcolor='grey95'
        )
        graph.add_node(_n)

    def create_edges(self, graph: pydot.Dot, master: dict) -> NoReturn:
        for _f in self.fields:
            if 'rc' in self.fields[_f]:
                _re = master[self.fields[_f]['re']]
                _rc = self.fields[_f]['rc']
                _e = pydot.Edge(
                    f"{_re.meta['table']}",
                    f"{self.meta['table']}",
                    tailport=f"f{_re.fields[_rc]['fid']}",
                    headport=f"f{self.fields[_f]['fid']}",
                    color=_re.color,
                    arrowhead='normal',
                    dir='forward'
                )
                graph.add_edge(_e)
        pass
