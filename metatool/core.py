"""
This module represents MetaTool API - set of functions purposed for
interaction with MetaCore cloud servers. Each function provides specific
type of operation with the MetaCore server. Look through the functions for
detailed specification.
"""
import sys
import os
import os.path
import requests

from hashlib import sha256

# 2.x/3.x compliance logic
if sys.version_info.major == 3:
    from urllib.parse import urljoin
else:
    from urlparse import urljoin


def audit(url_base, sender_key, btctx_api, file_hash, seed):
    """It make an request to the server with a view of calculating
    the SHA-256 hash of a file plus some seed.
    Return the response object with information about the server-error
    when such has occurred.

    :param url_base: URL string which defines the server will be used
    :type url_base: string

    :param sender_key: unique secret key which will be used for the
        generating credentials required by the access to the server
    :type sender_key: string

    :param btctx_api: instance of the ``BtcTxStore`` class which will be used
        to generate credentials for the server access
    :type btctx_api: btctxstore.BtcTxStore object

    :param file_hash: hash-name of the file you are going to audit
    :type file_hash: string

    :param seed: (str) should be a SHA-256 hash of that you would like to add
        to the file data to generate a challenge response
    :type seed: string

    :returns: response instance with the results of challenge or with
        information about the server issue
    :rtype: requests.models.Response object
    """
    signature = btctx_api.sign_unicode(sender_key, file_hash)
    sender_address = btctx_api.get_address(sender_key)
    response = requests.post(
        urljoin(url_base, '/api/audit/'),
        data={
            'data_hash': file_hash,
            'challenge_seed': seed,
        },
        headers={
            'sender-address': sender_address,
            'signature': signature,
        }
    )
    return response


def download(url_base, sender_key, btctx_api, file_hash,
             rename_file=None, decryption_key=None, link=False):
    """
    It performs the downloading of the file from the server
    by the given ``file_hash``.
    If ``link=True`` will return GET-request URL-string instead of download,
    so you can use it like a simple URL address and download it through the
    browser.

    :note: The "link=True" case implies non-authenticated access to the
        file, available only for files with such values of ``roles``: 101, 001

    Will return the response object with information about the server-error
    when such has occurred.

    :param url_base: URL-string which defines the server will be used
    :type url_base: string

    :param sender_key: unique secret key which will be used for the
        generating credentials required by the access to the server
    :type sender_key: string

    :param btctx_api: instance of the ``BtcTxStore`` class which will be used
        to generate credentials for the server access
    :type btctx_api: btctxstore.BtcTxStore object

    :param file_hash: hash-name of the file you are going to audit
    :type file_hash: string

    :param rename_file: defines new name of the file after downloading

        (optional, default: None)
    :type rename_file: string

    :param decryption_key: key value which will be used to decrypt file
        on the server before the downloading (if allowed by the role)

        (optional, default: None)
    :type decryption_key: string

    :param link: if ``True``, function doesn't perform the downloading but
        generate appropriate GET URL-string instead

        (optional, default: False)
    :type link: boolean

    :returns: full path to the file if download done successfully

        :rtype: string
    :returns: if ``link=True``, will return GET-request
        URL-string, instead of processing the downloading

        :rtype: string
    :returns: object with information about the occurred error on the server
        while the downloading

        :rtype: requests.models.Response object
    """
    url_for_requests = urljoin(url_base, '/api/files/' + file_hash)

    params = {}
    if decryption_key:
        params['decryption_key'] = decryption_key

    if rename_file:
        params['file_alias'] = rename_file

    data_for_requests = dict(params=params)
    if link:
        request = requests.Request('GET', url_for_requests,
                                   **data_for_requests)
        request_string = request.prepare()
        return request_string.url

    signature = btctx_api.sign_unicode(sender_key, file_hash)
    sender_address = btctx_api.get_address(sender_key)

    data_for_requests['headers'] = {
        'sender-address': sender_address,
        'signature': signature,
    }

    response = requests.get(
        url_for_requests,
        **data_for_requests
    )

    if response.status_code == 200:
        file_name = os.path.join(os.getcwd(),
                                 response.headers['X-Sendfile'])

        with open(file_name, 'wb') as fp:
            fp.write(response.content)
        return file_name
    else:
        return response


def upload(url_base, sender_key, btctx_api, file, file_role):
    """
    Upload local file to the server. Max size of file is determined by the
    server. In the most of cases it is restricted by the 128 MB.
    Return the response object with ``file_hash`` and ``file_role`` when
    have done successfully or the server-error when such has occurred.

    :param url_base: URL-string which defines the server will be used
    :type url_base: string

    :param sender_key: unique secret key which will be used for the
        generating credentials required by the access to the server
    :type sender_key: string

    :param btctx_api: instance of the ``BtcTxStore`` class which will be used
        to generate credentials for the server access
    :type btctx_api: btctxstore.BtcTxStore object

    :param file: file object which will be uploaded to the server
    :type file: file object opened in the 'rb' mode

    :param file_role: three numbers string which define future behavior of the
        file on the server. See more about it in the documentation
    :type file_role: string

    :returns: response instance with the results of uploading or with
        information about the server issue
    :rtype: requests.models.Response object
    """
    files_header = {'file_data': file}
    data_hash = sha256(file.read()).hexdigest()
    file.seek(0)
    sender_address = btctx_api.get_address(sender_key)
    signature = btctx_api.sign_unicode(sender_key, data_hash)
    response = requests.post(
        urljoin(url_base, '/api/files/'),
        data={
            'data_hash': data_hash,
            'file_role': file_role,
        },
        files=files_header,
        headers={
            'sender-address': sender_address,
            'signature': signature,
        }
    )
    return response


def files(url_base):
    """
    It executes a request to the "Node" server and returns response object
    with json-string - the list of hashes of downloaded files.

    :param url_base: URL-string which defines the server will be used
    :type url_base: string

    :returns: response instance with a list of string - hashes of files
        available on the server or with information about the server issue
    :rtype: requests.models.Response object
    """
    response = requests.get(urljoin(url_base, '/api/files/'))
    return response


def info(url_base):
    """
    It executes a request to the "Node" server and returns response object
    with json-string - the information about server application state.

    :param url_base: URL-string which defines the server will be used
    :type url_base: string

    :returns: response instance with node state information or with
        information about the server issue
    :rtype: requests.models.Response object
    """
    response = requests.get(urljoin(url_base, '/api/nodes/me/'))
    return response