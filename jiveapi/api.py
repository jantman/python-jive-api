"""
The latest version of this package is available at:
<http://github.com/jantman/jiveapi>

##################################################################################
Copyright 2017 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

    This file is part of jiveapi, also known as jiveapi.

    jiveapi is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    jiveapi is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with jiveapi.  If not, see <http://www.gnu.org/licenses/>.

The Copyright and Authors attributions contained herein may not be removed or
otherwise altered, except to add the Author attribution of a contributor to
this work. (Additional Terms pursuant to Section 7b of the AGPL v3)
##################################################################################
While not legally required, I sincerely request that anyone who finds
bugs please submit them at <https://github.com/jantman/jiveapi> or
to me via email, and that you send any contributions or improvements
either as a pull request on GitHub, or to me via email.
##################################################################################

AUTHORS:
Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>
##################################################################################
"""

import logging
import requests
from urllib.parse import urljoin, quote_plus
import re
import json

from jiveapi.jiveresponse import requests_hook
from jiveapi.exceptions import RequestFailedException, ContentConflictException

logger = logging.getLogger(__name__)

#: API url param timestamp format, like '2012-01-31T22:46:12.044+0000'
#: note that sub-second time is ignored and set to zero.
TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.000%z'


class JiveApi(object):

    def __init__(self, base_url, username, password):
        """
        Initialize JiveApi client.

        :param base_url: Base URL to the Jive API. This should be the scheme,
          hostname, and optional port with nothing after it (i.e. no ``/api``).
        :type base_url: str
        :param username: Jive API username
        :type username: str
        :param password: Jive API password
        :type password: str
        """
        self._base_url = base_url
        if not self._base_url.endswith('/'):
            self._base_url += '/'
        self._username = username
        self._password = password
        self._requests = requests.Session()
        # add the requests hook to use JiveResponse() class
        self._requests.hooks['response'].append(requests_hook)
        # setup auth
        self._requests.auth = (self._username, self._password)

    def _get(self, path, autopaginate=True):
        """
        Execute a GET request against the Jive API, handling pagination.

        :param path: path or full URL to GET
        :type path: str
        :param autopaginate: If True, automatically paginate multi-page
          responses and return a list of the combined results. Otherwise,
          return the unaltered JSON response.
        :type autopaginate: bool
        :return: deserialized response JSON. Usually dict or list.
        """
        if path.startswith('http://') or path.startswith('https://'):
            # likely a pagination link
            url = path
        else:
            url = urljoin(self._base_url, path)
        logger.debug('GET %s', url)
        res = self._requests.get(url)
        logger.debug('GET %s returned %d %s', url, res.status_code, res.reason)
        if res.status_code > 299:
            raise RequestFailedException(res)
        j = res.json()
        if not isinstance(j, type({})) or 'list' not in j or not autopaginate:
            return j
        # else has a 'list' key
        if 'links' not in j or 'next' not in j['links']:
            return j['list']
        # it has another page
        return j['list'] + self._get(j['links']['next'])

    def _post_json(self, path, data):
        """
        Execute a POST request against the Jive API, sending JSON.

        :param path: path or full URL to POST to
        :type path: str
        :param data: Data to POST.
        :type data: ``dict`` or ``list``
        :return: deserialized response JSON. Usually dict or list.
        """
        if path.startswith('http://') or path.startswith('https://'):
            # likely a pagination link
            url = path
        else:
            url = urljoin(self._base_url, path)
        logger.debug('POST to %s (length %d)', url, len(json.dumps(data)))
        res = self._requests.post(url, json=data)
        logger.debug(
            'POST %s returned %d %s', url, res.status_code, res.reason
        )
        if res.status_code > 299:
            raise RequestFailedException(res)
        return res.json()

    def _put_json(self, path, data):
        """
        Execute a PUT request against the Jive API, sending JSON.

        :param path: path or full URL to PUT to
        :type path: str
        :param data: Data to POST.
        :type data: ``dict`` or ``list``
        :return: deserialized response JSON. Usually dict or list.
        """
        if path.startswith('http://') or path.startswith('https://'):
            # likely a pagination link
            url = path
        else:
            url = urljoin(self._base_url, path)
        logger.debug('PUT to %s (length %d)', url, len(json.dumps(data)))
        res = self._requests.put(url, json=data)
        logger.debug(
            'PUT %s returned %d %s', url, res.status_code, res.reason
        )
        if res.status_code > 299:
            raise RequestFailedException(res)
        return res.json()

    def user(self, id_number='@me'):
        """
        Return dict of information about the specified user.

        :param id_number: User ID number. Defaults to ``@me``, the current user
        :type id_number: str
        :return: user information
        :rtype: dict
        """
        return self._get('core/v3/people/%s' % id_number)

    def api_version(self):
        """
        Get the Jive API version information

        :return: raw API response dict for ``/version`` endpoint
        :rtype: dict
        """
        return self._get('version')

    def _escape_query_string(self, s):
        """Escape a query string for Jive's god-awful API queries"""
        return re.sub(r'(,|\(|\)|\\)', lambda m: '\%s' % m.group(), s)

    def get_content(self, content_id):
        """
        Given the content ID of a content object in Jive, return the API (dict)
        representation of that content object. This is the low-level direct API
        call that corresponds to `Get Content <https://developers.jivesoftware.
        com/api/v3/cloud/rest/ContentService.html#getContent%28String%2C%20Strin
        g%2C%20boolean%2C%20List%3CString%3E)>`_.

        This GETs content with the "Silent Directive" that prevents Jive read
        counts from being incremented. See
        `Silent Directive for Contents Service <https://community.jivesoftware.c
        om/docs/DOC-233174#>`_.

        :param content_id: the Jive contentID of the content
        :type content_id: str
        :return: content object representation
        :rtype: dict
        """
        return self._get('core/v3/contents/%s?directive=silent' % content_id)

    def create_content(self, contents, publish_date=None):
        """
        POST to create a new Content object in Jive. This is the low-level
        direct API call that corresponds to `Create content <https://developers
        .jivesoftware.com/api/v3/cloud/rest/ContentService.html#createContent%28
        String%2C%20String%2C%20String%2C%20String%29>`_. Please see
        the more specific wrapper methods if they suit your purposes.

        :param contents: A JSON-serializable Jive content representation,
          suitable for POSTing to the ``/contents`` API endpoint.
        :type contents: dict
        :param publish_date: A backdated publish and update date to set on the
          content. This allows publishing content with backdated publish dates,
          for migration purposes.
        :type publish_date: datetime.datetime
        :return: API response of Content object
        :rtype: dict
        """
        logger.debug('Creating content...')
        url = 'core/v3/contents'
        if publish_date is not None:
            dts = quote_plus(publish_date.strftime(TIME_FORMAT))
            logger.debug('Backdating content publish to %s (%s)',
                         publish_date, dts)
            url += '?published=%s&updated=%s' % (dts, dts)
        try:
            res = self._post_json(url, contents)
        except RequestFailedException as ex:
            if ex.status_code == 409:
                raise ContentConflictException(ex.response)
            raise
        logger.debug(
            'Created content with ID %s', res.get('contentID', 'unknown')
        )
        return res

    def create_html_document(self, subject, body):
        """
        Create a HTML Document in Jive. This is a convenience wrapper around
        :py:meth:`~.create_contents` to assist with forming the content JSON.

        Note that this cannot be used for Documents with attachments (i.e.
        images); you either need to upload the attachments separately or
        use @TODO.

        :param subject: The subject / title of the Document.
        :type subject: str
        :param body: The HTML body of the Document. See the notes in the jiveapi
          package documentation about HTML handling.
        :type body: str
        :return: representation of the created Document content object
        :rtype: dict
        """
        content = {
            'type': 'document',
            'subject': subject,
            'content': {
                'type': 'text/html',
                'text': body
            }
        }
        return self.create_content(content)

    def update_content(self, content_id, contents, update_date=None):
        """
        PUT to update an existing Content object in Jive. This is the low-level
        direct API call that corresponds to `Update content <https://developers.
        jivesoftware.com/api/v3/cloud/rest/ContentService.html#updateContent%28
        String%2C%20String%2C%20String%2C%20boolean%2C%20String%2C%20boolean
        %29>`_. Please see the more specific wrapper methods if they suit your
        purposes.

        **Warning:** In current Jive versions, it appears that editing/updating
        a (blog) Post will change the date-based URL to the post, breaking all
        existing links to it!

        :param content_id: The Jive contentID of the content to update.
        :type content_id: str
        :param contents: A JSON-serializable Jive content representation,
          suitable for POSTing to the ``/contents`` API endpoint.
        :type contents: dict
        :param update_date: A backdated update date to set on the content. This
          allows publishing content with backdated publish dates, for migration
          purposes.
        :type update_date: datetime.datetime
        :return: API response of Content object
        :rtype: dict
        """
        logger.debug('Updating content with contentID %s', content_id)
        url = 'core/v3/contents/%s' % content_id
        if update_date is not None:
            dts = quote_plus(update_date.strftime(TIME_FORMAT))
            logger.debug('Backdating content update to %s (%s)',
                         update_date, dts)
            url += '?updated=%s' % dts
        try:
            res = self._put_json(url, contents)
        except RequestFailedException as ex:
            if ex.status_code == 409:
                raise ContentConflictException(ex.response)
            raise
        logger.debug(
            'Updated content with ID %s', res.get('contentID', 'unknown')
        )
        return res

    def get_image(self, image_id):
        """
        GET the image specified by ``image_id`` as binary content. This method
        currently can only retrieve the exact original image. This is the
        low-level direct API call that corresponds to `Get Image <https://devel
        opers.jivesoftware.com/api/v3/cloud/rest/ImageService.html#getImage%28S
        tring%2C%20String%2C%20String%2C%20String%2C%20String%29>`_.

        :param image_id: Jive Image ID to get. This can be found in a Content
        (i.e. Document or Post) object's ``contentImages`` list.
        :type image_id: str
        :return: binary content of Image
        :rtype: bytes
        """
        # Testing Note: betamax==0.8.1 and/or betamax-serializers==0.2.0 cannot
        # handle testing the binary response content from this method.
        url = urljoin(self._base_url, 'core/v3/images/%s' % image_id)
        logger.debug('GET (binary) %s', url)
        res = self._requests.get(url)
        logger.debug(
            'GET %s returned %d %s (%d bytes)', url, res.status_code,
            res.reason, len(res.content)
        )
        if res.status_code > 299:
            raise RequestFailedException(res)
        return res.content

    def upload_image(self, img_data, img_filename, content_type):
        """
        Upload a new Image resource to be stored on the server as a temporary
        image, i.e. for embedding in an upcoming Document, Post, etc. Returns
        Image object and the user-facing URI for the image itself, i.e.
        ``https://sandbox.jiveon.com/api/core/v3/images/601174?a=1522503578891``

        **Note:** Python's ``requests`` lacks streaming file support. As such,
        images sent using this method will be entirely read into memory and then
        sent. This may not work very well for extremely large images.

        **Warning:** As far as I can tell, the user-visible URI to an image
        can *only* be retrieved when the image is uploaded. There does not seem
        to be a way to get it from the API for an existing image.

        :param img_data: The binary image data.
        :type img_data: bytes
        :param img_filename: The filename for the image. This is purely for
          display purposes.
        :type img_filename: str
        :param content_type: The MIME Content Type for the image data.
        :type content_type: str
        :return: 2-tuple of (string user-facing URI to the image i.e. for use
          in HTML, dict Image object representation)
        :rtype: tuple
        """
        # Testing Note: betamax==0.8.1 and/or betamax-serializers==0.2.0 cannot
        # handle testing the binary response content from this method.
        url = urljoin(self._base_url, 'core/v3/images')
        files = {
            'file': (img_filename, img_data, content_type)
        }
        logger.debug('POST to %s (length %d)', url, len(img_data))
        res = self._requests.post(url, files=files, allow_redirects=False)
        logger.debug(
            'POST %s returned %d %s', url, res.status_code, res.reason
        )
        if res.status_code != 201:
            raise RequestFailedException(res)
        logger.debug(
            'Uploaded image with Location: %s', res.headers['Location']
        )
        return res.headers['Location'], res.text


"""
## Document with embedded images GET example:

  "content" : {
    "text" : "<body><!-- [DocumentBodyStart:1693a4b1-d031-49cf-89f0-c768af9badbd] --><div class=\"jive-rendered-content\"><p>This is one image&#160;<a href=\"https://<JIVE-HOST>/servlet/JiveServlet/showImage/102-181245-3-601173/20x20.png\"><img alt=\"image description 20x20\" class=\"image-2 jive-image j-img-original\" height=\"20\" src=\"https://<JIVE-HOST>/servlet/JiveServlet/downloadImage/102-181245-3-601173/20x20.png\" style=\"height: auto;\" width=\"20\"/></a> and this is another:&#160;<a href=\"https://<JIVE-HOST>/servlet/JiveServlet/showImage/102-181245-3-601172/25x25.png\"><img alt=\"image description 25x25\" class=\"image-1 jive-image j-img-original\" height=\"25\" src=\"https://<JIVE-HOST>/servlet/JiveServlet/downloadImage/102-181245-3-601172/25x25.png\" style=\"height: auto;\" width=\"25\"/></a></p></div><!-- [DocumentBodyEnd:1693a4b1-d031-49cf-89f0-c768af9badbd] --></body>",
    "editable" : false,
    "type" : "text/html"
  },
  "contentImages" : [ {
    "id" : "601172",
    "ref" : "https://<JIVE-HOST>/api/core/v3/images/601172?a=1522455592480",
    "size" : 167,
    "width" : 25,
    "height" : 25,
    "type" : "image",
    "typeCode" : 111
  }, {
    "id" : "601173",
    "ref" : "https://<JIVE-HOST>/api/core/v3/images/601173?a=1522455592433",
    "size" : 165,
    "width" : 20,
    "height" : 20,
    "type" : "image",
    "typeCode" : 111
  } ],
  "attachments" : [ ],

## Adding Embedded Images to Content:
https://community.jivesoftware.com/docs/DOC-233174#jive_content_id_Adding_Embedded_Images_to_a_Piece_of_Content

1. Upload Image (POST multipart/form-data) See: Images Service
2. Read Location HTTP Header for API URI for Image
3. Add HTML Markup in Content Body using the new API URI for the Image, see: Contents Service > Update Content
  * May find value in the Contents Service > Update Editable Content if you want to leverage RTE macros.
    * Note the documentation callout : The input JSON must include a true value in content.editable if the content body is using RTE macros.

## Stuff about Editable Content and RTE Macros
https://developers.jivesoftware.com/api/v3/cloud/rest/ContentService.html#updateEditableContent(String, String, boolean, boolean, String)

## Performance Note:
see https://community.jivesoftware.com/docs/DOC-233174#jive_content_id_Suppressing_Fields_from_API_Responses

"""