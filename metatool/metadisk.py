#! /usr/bin/env python3
"""\
===========================================
welcome to the metatool help information
===========================================

usage:
metatool <action> [ appropriate | arguments | for actions ] [--url URL_ADDR]

"metatool" expect the main first positional argument <action> which define
the action of the program. Must be one of:

    files | info | upload | download | audit

Each of actions expect an appropriate set of arguments after it. They are
separately described below.
Example:

    metatool upload ~/path/to/file.txt --file_role 002

The "--url" optional argument define url address of the target server.
In example:

    metatool info --url http://dev.storj.anvil8.com

But by default the server is "http://dev.storj.anvil8.com/" as well :)
You can either set an system environment variable "MEATADISKSERVER" to
provide target server instead of using the "--url" opt. argument.
------------------------------------------------------------------------------
SPECIFICATION THROUGH ALL OF ACTIONS
Each action return response status as a first line and appropriate data for
a specific action.
When an error is occur whilst the response it will be shown instead of
the success result.

... files
            Return the list of hash-codes of files uploaded at the server or
            return an empty list in the files absence case.

... info
            Return a json file with an information about the data usage of
            the node.

... upload <path_to_file> [-r | --file_role <FILE_ROLE>]
            Upload file to the server.

        <path_to_file> - Name of the file from the working directory
                         or a full/related path to the file.

        [-r | --file_role <FILE_ROLE>]  -  Key "-r" or "--file_role" purposed
                for the setting desired "file role". 001 by default.

            Return a json file with two fields of the information about
            the downloaded file.

... audit <data_hash> <challenge_seed>
            This action purposed for checkout the existence of files on the
            server (in opposite to plain serving hashes of files).
            Return a json file of three files with the response data:
                {
                  "challenge_response": ... ,
                  "challenge_seed": ... ,
                  "data_hash": ... ,
                }

... download <file_hash> [--decryption_key KEY] [--rename_file NEW_NAME]
                                                [--link]
            This action fetch desired file from the server by the "hash name".
            Return nothing if the file downloaded successful.

        <file_hash> - string with represent the "file hash".

        [--link] - will return the url GET request string instead of
                executing the downloading.

        [--decryption_key KEY] - Optional argument. When is defined the file
                downloading from the server in decrypted state (if allowed for
                this file).

            !!!WARNING!!! - will rewrite existed files with the same name!
        [--rename_file NEW_NAME] - Optional argument which define the NAME for
                storing file on your disk. You can indicate an relative and
                full path to the directory with this name as well.
"""
import sys
import os
import os.path
import argparse
import requests

from hashlib import sha256
from btctxstore import BtcTxStore
# 2.x/3.x compliance logic
if sys.version_info.major == 3:
    from urllib.parse import urljoin
else:
    from urlparse import urljoin


def set_up():
    global btctx_api, sender_key, sender_address, redirect_error_status

    redirect_error_status = (400, 404, 500, 503)
    btctx_api = BtcTxStore(testnet=True, dryrun=True)
    sender_key = btctx_api.create_key()
    sender_address = btctx_api.get_address(sender_key)


def _show_data(response):
    """
    Method to show data in console
    :param response: response from BtcTxStore node
    :return: None
    """
    print(response.status_code)
    print(response.text)


def action_audit(args):
    """
    Action method for audit command
    :return: None
    """
    signature = btctx_api.sign_unicode(sender_key, args.file_hash)

    response = requests.post(
        urljoin(args.url_base, '/api/audit/'),
        data={
            'data_hash': args.file_hash,
            'challenge_seed': args.seed,
        },
        headers={
            'sender-address': sender_address,
            'signature': signature,
        }
    )
    return response


def action_download(args):
    """
    Action method for download command
    :return: None
    """
    signature = btctx_api.sign_unicode(sender_key, args.file_hash)
    params = {}

    if args.decryption_key:
        params['decryption_key'] = args.decryption_key

    if args.rename_file:
        params['file_alias'] = args.rename_file

    data_for_requests = dict(
        params=params,
        headers={
            'sender-address': sender_address,
            'signature': signature,
        }
    )
    url_for_requests = urljoin(args.url_base, '/api/files/' + args.file_hash)
    request = requests.Request('GET', url_for_requests, **data_for_requests)
    if args.link:
        request_string = request.prepare()
        print(request_string.url)
    else:
        response = requests.get(
            url_for_requests,
            **data_for_requests
        )

        if response.status_code == 200:
            file_name = os.path.join(os.getcwd(),
                                     response.headers['X-Sendfile'])

            with open(file_name, 'wb') as fp:
                fp.write(response.content)
            print('saved as {}'.format(file_name))
            return
        else:
            return response


def action_upload(args):
    """
    Action method for upload command
    :return: None
    """
    files = {'file_data': args.file}
    data_hash = sha256(args.file.read()).hexdigest()
    args.file.seek(0)
    signature = btctx_api.sign_unicode(sender_key, data_hash)

    response = requests.post(
        urljoin(args.url_base, '/api/files/'),
        data={
            'data_hash': data_hash,
            'file_role': args.file_role,
        },
        files=files,
        headers={
            'sender-address': sender_address,
            'signature': signature,
        }
    )
    return response


def action_files(args):
    """
    Action method for files command
    :return: None
    """
    response = requests.get(urljoin(args.url_base, '/api/files/'))
    return response


def action_info(args):
    """
    Action method for info command
    :return: None
    """
    response = requests.get(urljoin(args.url_base, '/api/nodes/me/'))
    return response


def main():
    core_nodes = ('http://node2.metadisk.org/', 'http://node3.metadisk.org/')
    # Get the url from environment variable
    env_node = os.getenv('MEATADISKSERVER', None)
    used_nodes = (env_node,) if env_node else core_nodes

    if (len(sys.argv) == 1) or (sys.argv[1] in ['-h', '-help', '--help']):
        print(__doc__)
    else:
        response = None
        for url_base in used_nodes:
            set_up()
            parsed_args = parse(url_base)
            response = parsed_args.func(parsed_args)
            if not isinstance(response, requests.models.Response):
                return
            if response.status_code not in redirect_error_status:
                break
        _show_data(response)


def parse(url_base):
    """
    Parsing logic of the METATOOL.
    :return: parser object
    """
    # create the top-level parser
    main_parser = argparse.ArgumentParser(prog='METATOOL')
    main_parser.add_argument('--url', type=str, dest='url_base',
                             default=url_base)
    subparsers = main_parser.add_subparsers(help='sub-command help')

    # Create the parser for the "audit" command.
    parser_audit = subparsers.add_parser('audit', help='define audit purpose!')
    parser_audit.add_argument('file_hash', type=str, help="file hash")
    parser_audit.add_argument('seed', type=str, help="challenge seed")
    parser_audit.set_defaults(func=action_audit)

    # Create the parser for the "download" command.
    parser_download = subparsers.add_parser('download',
                                            help='define download purpose!')
    parser_download.add_argument('file_hash', type=str, help="file hash")
    parser_download.add_argument('--decryption_key', type=str,
                                 help="decryption key")
    parser_download.add_argument('--rename_file', type=str, help="rename file")
    parser_download.add_argument('--link', action='store_true',
                                 help='will return rust url for man. request')
    parser_download.set_defaults(func=action_download)

    # create the parser for the "upload" command.
    parser_upload = subparsers.add_parser('upload',
                                          help='define upload purpose!')
    parser_upload.add_argument('file', type=argparse.FileType('rb'),
                               help="path to file")
    parser_upload.add_argument('-r', '--file_role', type=str, default='001',
                               help="set file role")
    parser_upload.set_defaults(func=action_upload)

    # create the parser for the "files" command.
    parser_files = subparsers.add_parser('files', help='define files purpose!')
    parser_files.set_defaults(func=action_files)

    # create the parser for the "info" command.
    parser_info = subparsers.add_parser('info', help='define info purpose!')
    parser_info.set_defaults(func=action_info)

    # parse the commands
    return main_parser.parse_args()


if __name__ == '__main__':
    main()
