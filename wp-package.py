#!/usr/bin/python3

from typing import List
from collections import namedtuple

import argparse

import os, re
import datetime
from pathlib import Path

Database = namedtuple('Database', 'db_name db_user db_host db_password')

db_prop_exp = "define\\(\s{0,1}'(DB_USER|DB_HOST|DB_NAME|DB_PASSWORD)', '(.*)'\s{0,1}\\);"

now = datetime.datetime.now()
dateFormat = '%Y-%m-%d_%H%M'
date = now.strftime(dateFormat)

parser = argparse.ArgumentParser(description='Wordpress packager.')

parser.add_argument('directories', metavar='dirs', 
    type=str, nargs='+', help='wordpress directories')
parser.add_argument('-o', '--output', dest='output', 
    type=str, help='output directory', required=True)
parser.add_argument('-d', '--dry-run', dest='dry_run', action='store_true')
 
args = parser.parse_args()

def process_directory(dir: str):
    print(f'Processing dir {dir}')
    configs = find_configs(dir)
    if len(configs) == 0:
        print(f"No wordpress configs found, skipping {dir}...")
    else:
        print(f"Configs found: {configs}")
        sql_dump_files = []
        for wp_config in configs:
            db_config = parse_config(wp_config)
            sql_dump_file = dump_sql(db_config)
            sql_dump_files.append(sql_dump_file)

        create_tarball(dir, sql_dump_files)

        for sql_dump_file in sql_dump_files:
            rm = f'rm {sql_dump_file}'
            print(rm)
            if not args.dry_run:
                os.system(rm)

def find_configs(root: str) -> List[str]:
    found = []
    for dirname, _, filenames in os.walk(root):

        for filename in filenames:
            if filename == "wp-config.php":
                found.append(os.path.join(dirname, filename))
    
    return found

def parse_config(path: str) -> Database:
    db_props = dict()
    with open(path) as config_file:
        for line in config_file.readlines():
            match = re.search(db_prop_exp, line)
            if match:
                db_prop, db_value = match.groups()
                db_props[db_prop.lower()] = db_value
    print(db_props)
    return Database(**db_props)

def dump_sql(config: dict) -> str:
    dump_file = os.path.join(args.output, f'{config.db_name}_{date}.dump.sql')
    sql_dump = f'mysqldump -u {config.db_user} --no-tablespaces --password={config.db_password} {config.db_name} > {dump_file}'
    print(sql_dump)
    if not args.dry_run:
        os.system(sql_dump)
    return dump_file

def create_tarball(dir: str, sql_dump_files: List[str]):

    def content(path: str) -> str:
        path = Path(path)
        return f'-C {path.parent.absolute()} {path.name}'

    content_params = map(content, [dir, *sql_dump_files])
    dir_path = Path(dir)
    output = os.path.join(args.output, f'{dir_path.name}_{date}.tar.gz')
    
    tar = ' '.join(
        [
            f'tar czf {output}',
            *content_params
        ]
    )
    
    print(tar)
    if not args.dry_run:
        os.system(tar)

for file in args.directories:
    if os.path.isdir(file):
        process_directory(file)
    else: 
        print(f'Skipping file {file}')

