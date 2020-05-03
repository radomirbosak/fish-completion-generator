#!/usr/bin/env python3

import yaml, json,sys
from collections import defaultdict




functions = '''
function __fish_directly_after
    set -l cmdln (commandline -poc)
    if contains -- $cmdln[-1] $argv
        return 0
    end
    return 1
end
'''

def get_rootval(obj):
    assert len(obj) == 1
    key = list(obj.keys())[0]
    value = obj[key]
    return key, value

def decompose_base(base):
    if base.startswith('('):
        return '', '', '', base.strip()

    if not base.startswith('-'):
        description = ''
        if ' ' in base:
            base, description = base.split(' ', maxsplit=1)
        return '', '', description.strip(), base.strip()


    short, long = '', ''
    while ' ' in base:
        option, rest = base.split(' ', maxsplit=1)
        # print(base, option, rest)
        if option.startswith('--'):
            long = option[2:]
        elif option.startswith('-'):
            short = option[1:]
        else:
            break
        base = rest

    if base.startswith('--'):
        long = base[2:]
        base = ''
    elif base.startswith('-'):
        short = base[1:]
        base = ''

    base = base.strip()
    # sys.exit(1)
    return short, long, base, ''

class BlabItem:

    def __init__(self, node, cmd='', subcmd=''):
        self.cmd = cmd
        self.subcmd = subcmd

        self.short = None
        self.long = None
        self.string = None
        self.subnode = None
        self.choices = None
        self.children = []

        if type(node) == dict:
            base, self.subnode = get_rootval(node)
            self.base = base
            """
            list: unwatched watching watched dropped all
            edit:
                - (addb list all --raw-alias-list-desc)
                - --full-name
                - --alias
                - --status: watched unwatched watching dropped
            """

        if type(node) == str:
            base = node

        self.short, self.long, self.description, self.string = decompose_base(base) 

        if type(node) == dict:
            if type(self.subnode) == str:
                self.subnode = self.subnode.strip()
                self.choices = self.subnode
            elif type(self.subnode) == list:
                self.children = [BlabItem(child, cmd=cmd, subcmd= self.long or self.short or self.string)
                                 for child in self.subnode]
            else:
                raise NotImplementedError

    @property
    def shortpart(self):
        return ' -s ' + self.short if self.short else ''

    @property
    def longpart(self):
        return ' -l ' + self.long if self.long else ''

    @property
    def descpart(self):
        return ' --description "' + self.description + '"' if self.description else ''

    def compose_line(self, choices='', conditions=None):
        if not conditions:
            conditions = list()
        cmd = self.cmd
        shortpart = self.shortpart
        longpart = self.longpart
        descpart = self.descpart
        if self.subcmd:
            if shortpart or longpart:
                conditions.append('__fish_seen_subcommand_from ' + self.subcmd)
            else:
                conditions.append('__fish_directly_after ' + self.subcmd)
        conditions = " -n '" + '; and '.join(conditions) + "'" if conditions else ''
        choices = " -a '" + choices + "'" if choices else ''
        return f'complete -c {cmd}{conditions}{shortpart}{longpart}{descpart}{choices}'

    def compose_option_line(self, choices='', conditions=None):
        if not conditions:
            conditions = list()
        if self.subcmd:
            conditions.append('__fish_seen_subcommand_from ' + self.subcmd)
        cmd = self.cmd
        shortpart = ''
        longpart = ''
        descpart = ''
        conditions = " -n '" + '; and '.join(conditions) + "'" if conditions else ''
        choices = " -a '" + choices + "'" if choices else ''
        return f'complete -c {cmd}{conditions}{shortpart}{longpart}{descpart}{choices}'


    def option_itself(self):
        """
        -h
        --version
        watch
        """

        if self.string:
            # subcommand
            conditions = []
            if not self.subcmd:
                conditions = ['__fish_use_subcommand']
            return self.compose_line(choices=self.string, conditions=conditions)

        # short or long option
        return self.compose_line()

    def option_values(self):
        """
        -p tcp|udp
        --protocol tcp|udp
        list watched|unwatched|dropped
        """
        keyword = self.string
        if not keyword and self.short:
            keyword = '-' + self.short
        if not keyword and self.long:
            keyword = '--' + self.long

        return self.compose_option_line(choices=self.subnode, conditions=['__fish_directly_after ' + keyword])

    def print_recursively(self):
        print(self.option_itself())
        if self.choices:
            print(self.option_values())

        for child in self.children:
            child.print_recursively()


if len(sys.argv) < 2:
    print('Usage:')
    print(f'{sys.argv[0]} sample.yaml')
    sys.exit(1)


obj = yaml.load(open(sys.argv[1]), Loader=yaml.Loader)
assert len(obj) == 1

cmd, arguments = get_rootval(obj)

print(f'complete -c {cmd} -f')

for arg in arguments:
    item = BlabItem(arg, cmd=cmd)
    item.print_recursively()
