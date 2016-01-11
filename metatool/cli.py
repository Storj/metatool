"""
The ``metatool.cli`` module is a CLI application for the MetaCore service.
``metatool`` package can be used from the command line like python module::

    $ python -m metatool ...

or can be installed and used like usual CLI::

    $ metatool ...

======================
`metatool` CLI Usage
======================
Common syntax for all actions::

   metatool <action> [--url URL_ADDR] [ appropriate | arguments | for actions ]

"metatool" expect the main lead positional argument ``action`` which define
the action of the program. Must be one of::

    files | info | upload | download | audit

Each of actions expect an appropriate set of arguments after it. They are
separately described below.
Example::

    $ metatool upload ~/path/to/file.txt --file_role 002

The ``--url`` is the optional argument common for all the actions and defines
the URL-address of the target server. In example::

    $ metatool info --url http://dev.storj.anvil8.com

But by default the server is http://node2.metadisk.org .
You can either set an system environment variable ``MEATADISKSERVER`` to
provide target server instead of using the "--url" opt. argument.

------------------------------------

Guide through all of the actions
--------------------------------

Every action except ``download`` returns response status as a first line and
appropriate data for a specific action. When an error is occurs whilst the
response it will be shown instead of the success result.

**metatool files**
    Returns the list of hash-codes of files uploaded at the server or
    returns an empty list in the files absence case.

-------------------

**metatool info**
    Returns a json file with an information about the usage of data
    on the node.

-------------------

**metatool upload <path_to_file> [-r | --file_role FILE_ROLE]**
    Upload file to the server.

        ``path_to_file`` - Name of the file from the working directory
        or a *full/related* path to the file.

        ``-r | --file_role FILE_ROLE``  -  Key **-r** or **--file_role**
        purposed for the setting desired **file_role**. **001** by default.

    Returns a json file with **data_hash** and **file_role**.

-------------------

**metatool audit <data_hash> <challenge_seed>**
    This action purposed for checking out the existence of files on the
    server (in opposite to plain serving hashes of files).
    Return a json file of three files with the response data::

        {
          "challenge_response": ... ,
          "challenge_seed": ... ,
          "data_hash": ... ,
        }

-------------------

**metatool download <file_hash> [--decryption_key KEY]
[--rename_file NEW_NAME] [--link]**

    This action fetch desired file from the server by the **hash_name**.
    Returns full path to the file if downloaded successful.

        ``file_hash`` - string which represents the **file hash**.

        ``--link`` - will return the url GET request string instead of
        executing the downloading.

        ``--decryption_key KEY`` - Optional argument. When defined the file si
        going from the server in decrypted state (if allowed for this file).

        :note: will rewrite existed file with the same name!

        ``--rename_file NEW_NAME`` - Optional argument which defines
        the **NEW_NAME** for the storing file on your disk. You can provide
        an relative and full path to the directory with this name as well.

=========================================
`metatool.cli` function's specification
=========================================
"""
from __future__ import print_function
import os.path
import sys
import argparse

from btctxstore import BtcTxStore

# makes available to import package from the source directory
parent_dir = os.path.dirname(os.path.dirname(__file__))
if not parent_dir in sys.path:
    sys.path.insert(0, parent_dir)
import metatool.core

CORE_NODES_URL = ('http://node2.metadisk.org/', 'http://node3.metadisk.org/')


def parse():
    """
    Set of the parsing logic for the METATOOL.
    It doesn't perform parsing, just fills the parser object with arguments.

    :returns: fully configured ArgumentParser instance
    :rtype: argparse.ArgumentParser object
    """
    # Create the top-level parser.
    main_parser = argparse.ArgumentParser(
        prog='METATOOL',
        description="This is the console app intended for interacting with "
                    "the MetaCore server.",
        epilog="    Note: Use -h or --help argument with any of actions "
               "to show detailed help info."
    )
    subparsers = main_parser.add_subparsers(
            help="It's a choose which action to perform.")

    # Create a parent parser with common ``--url`` optional argument.
    parent_url_parser = argparse.ArgumentParser(
        add_help=None
    )
    parent_url_parser.add_argument('--url', type=str, dest='url_base',
                             help='The URL-string which defines the '
                                  'server will be used.')


    # Create the parser for the "audit" command.
    parser_audit = subparsers.add_parser(
        'audit',
        parents=[parent_url_parser],
        help='It makes an request to the server with a view of calculating '
             'the SHA-256 hash of a file plus some seed.'
    )
    parser_audit.add_argument('file_hash', type=str,
                              help="The hash of the challenged file.")
    parser_audit.add_argument('seed', type=str,
                              help="Hash-value that will be added to "
                                   "the file's data to challenging the file.")
    parser_audit.set_defaults(execute_case=metatool.core.audit)

    # Create the parser for the "download" command.
    parser_download = subparsers.add_parser(
        'download',
        parents=[parent_url_parser],
        help='It performs the downloading of the file from the server'
             'by a given file_hash.'
    )
    parser_download.add_argument('file_hash', type=str, help="A file's hash.")
    parser_download.add_argument('--decryption_key', type=str,
                                 help="The key to decrypt the file "
                                      "while downloading.")
    parser_download.add_argument('--rename_file', type=str,
                                 help="It defines how to rename the file "
                                      "while downloading.")
    parser_download.add_argument('--link', action='store_true',
                                 help='If argument is present it will return '
                                      'an URL-string for a manual downloading')
    parser_download.set_defaults(execute_case=metatool.core.download)

    # create the parser for the "upload" command.
    parser_upload = subparsers.add_parser(
        'upload',
        parents=[parent_url_parser],
        help='It uploads a local file to the server.'
    )
    parser_upload.add_argument('file', type=argparse.FileType('rb'),
                               help="A path to the file")
    parser_upload.add_argument('-r', '--file_role', type=str, default='001',
                               help="It defines behaviour and access "
                                    "of the file.")
    parser_upload.set_defaults(execute_case=metatool.core.upload)

    # create the parser for the "files" command.
    parser_files = subparsers.add_parser(
        'files',
        parents=[parent_url_parser],
        help="It gets the list with hashes of files on the server.")
    parser_files.set_defaults(execute_case=metatool.core.files)

    # create the parser for the "info" command.
    parser_info = subparsers.add_parser(
        'info',
        parents=[parent_url_parser],
        help="It gets the information about the server's application state.")
    parser_info.set_defaults(execute_case=metatool.core.info)

    return main_parser


def show_data(data):
    """
    Method used to show the action processing data in the console.

    :param data: response object or string data generated
        by the core API functions
    :type data: string
    :type data: requests.models.Response object

    :returns: None
    """
    if isinstance(data, str):
        print(data)
    else:
        print(data.status_code, data.text, sep='\n')


def args_prepare(required_args, parsed_args):
    """
    Filling all missed but required by the core API function arguments.
    Return dictionary that will be passed to the API function.

    :param required_args: list of required argument's names for
        the API function
    :type required_args: list of stings
    :param parsed_args: can be any object with appropriate names of attributes
        required by the core API function
    :type parsed_args: argparse.Namespace

    :returns: dictionary that will be used like `**kwargs` argument
    :rtype: dictionary
    """
    btctx_api = BtcTxStore(testnet=True, dryrun=True)
    prepared_args = {}
    args_base = dict(
        sender_key=btctx_api.create_key(),
        btctx_api=btctx_api,
    )
    for required_arg in required_args:
        try:
            prepared_args[required_arg] = getattr(parsed_args, required_arg)
        except AttributeError:
            prepared_args[required_arg] = args_base[required_arg]
    return prepared_args


def get_all_func_args(function):
    """
    It finds out all available arguments of the given function.
    :param function: function object to inspect.
    :type function: function object

    :returns: list with names of all available arguments
    :rtype: list of strings
    """
    return function.__code__.co_varnames[:function.__code__.co_argcount]


def main():
    """
    The main **MetaTool** CLI logic. It parses arguments, defines the type of
    action an appropriate API function, prepares parsed arguments and call
    the interact with appropriate Node MetaCore server.
    """
    redirect_error_status = (400, 404, 500, 503)
    if len(sys.argv) == 1:
        parse().print_help()
        return
    args = parse().parse_args()
    parsed_args = args_prepare(get_all_func_args(args.execute_case), args)

    # Get the url from the environment variable
    # or from the "--url" parsed argument
    env_node = os.getenv('MEATADISKSERVER', None)
    used_nodes = (env_node,) if env_node else CORE_NODES_URL
    used_nodes = (args.url_base,) if args.url_base else used_nodes

    result = "Sorry, nothing has done."
    for url_base in used_nodes:
        parsed_args['url_base'] = url_base
        result = args.execute_case(**parsed_args)
        if isinstance(result, str):
            break
        if result.status_code not in redirect_error_status:
            break
    show_data(result)