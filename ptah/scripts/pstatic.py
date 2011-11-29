""" static commands """
import os.path, shutil
import argparse
import textwrap
from pyramid import testing

from ptah import config
from ptah.view import resources


grpTitleWrap = textwrap.TextWrapper(
    initial_indent='* ',
    subsequent_indent='  ',
    width = 80)

nameWrap = textwrap.TextWrapper(
    initial_indent='  - ',
    subsequent_indent='    ', width = 80)

overWrap = textwrap.TextWrapper(
    initial_indent='      ',
    subsequent_indent='      ', width = 80)

nameTitleWrap = textwrap.TextWrapper(
    initial_indent='       ',
    subsequent_indent='       ', width = 80)

def main():
    args = StaticCommand.parser.parse_args()
    cmd = StaticCommand(args)
    cmd.run()


class StaticCommand(object):
    """ 'static' command"""

    parser = argparse.ArgumentParser(
        description="ptah static assets management")
    parser.add_argument('-l', '--list', dest='section',
                        action="store_true",
                        help = 'List registered static sections')
    parser.add_argument('-d', '--dump', dest='dump',
                        help = 'Dump static assets')

    _include = None # tests

    def __init__(self, args):
        self.options = args

    def run(self):
        # load all ptah packages
        pconfig = testing.setUp()
        pconfig.include('ptah')
        config.initialize(pconfig, self._include, autoinclude=True)
        registry = config.get_cfg_storage(resources.STATIC_ID)

        if self.options.dump:
            basepath = self.options.dump.strip()
            if not os.path.exists(basepath):
                os.makedirs(basepath)

            if not os.path.isdir(basepath):
                print "Output path is not directory."
                return

            items = registry.items()
            items.sort()
            for name, (path, pkg) in items:
                print "* Coping from '%s' %s"%(pkg, path)

                d = resources.buildTree(path)
                di = d.items()
                di.sort()

                for p, _t in di:
                    bp = os.path.join(basepath, name, p)
                    dest_dir = os.path.split(bp)[0]
                    if not os.path.exists(dest_dir):
                        os.makedirs(dest_dir)

                    forp = '%s/%s'%(pkg, p.split(pkg, 1)[-1])
                    if os.path.exists(bp):
                        print '   skipping ../%s'%forp
                    else:
                        print '   coping ../%s'%forp
                        shutil.copyfile(os.path.join(path, p), bp)

                print

            print basepath
            return

        # list static sections
        if self.options.section:
            items = registry.items()
            items.sort()

            for name, (path, pkg) in items:
                print grpTitleWrap.fill(name)
                print nameWrap.fill('by: %s'%pkg)
                p = path.split(pkg, 1)[-1]
                print nameTitleWrap.fill(' ../%s%s'%(pkg, p))
                print