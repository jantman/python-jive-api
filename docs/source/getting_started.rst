.. _getting_started:

Getting Started
===============

.. _local_installation:

Local Installation
------------------

``pip install jiveapi``

.. _docker_installation:

Use via Docker Image
--------------------

``docker pull jantman/jiveapi:VERSION`` where ``VERSION`` is the desired `release version <https://github.com/jantman/jiveapi/releases>`_.

For Docker usage examples, see :ref:`Docker Examples <docker_examples>`.

.. _authentication:

Authentication
--------------

Version 3 of the Jive ReST API is rather limited in terms of `Authentication methods <https://developer.jivesoftware.com/intro/#building-an-api-client>`_: OAuth is only supported for Jive Add-Ons. The alternative is HTTP Basic, which is not supported for federated/SSO accounts. This project uses HTTP Basic auth, which requires a Jive local (service) account.

.. _important_notes:

Important Notes
---------------

.. _content_ids:

Content IDs
+++++++++++

When a Content object (e.g. Document, Post, etc.) is created in Jive it is assigned a unique contentID. This contentID must be provided in order to update or delete the content. It is up to you, the user, to store the contentIDs generated by this package when you create content objects. For example use it's enough to record them from the CLI output. For actual production use, I recommend using the Python API and storing the returned IDs in a database or key/value store, or committing them back to the git repository. Also note that even though I've never seen a Jive contentID that isn't ``^[0-9]+$``, the Jive API JSON presents and accepts them as strings and the API type documentation lists them as strings.

For most Jive objects, you can obtain the ID by viewing it in the web interface and appending ``/api/v3`` to the URL. i.e. if you have a Space at ``https://sandbox.jiveon.com/community/developertest``, you can find its contentID in the JSON returned from ``https://sandbox.jiveon.com/community/developertest/api/v3``. It is **important** to note that the "id" field of the JSON is *not* the same as the "contentID" field.

.. _html_notes:

HTML
++++

Jive's HTML handling is somewhat finnicky. This package includes code that attempts to compensate for that. In addition to some very specific styling required to get input HTML to look correct in Jive, Jive also does some annoying things like:

* Removing or overwriting the ``id`` attributes of HTML elements.
* Assigning its own ``id`` attributes to anchors.
* Not allowing links to anchors with names including hyphens; they will be silently ignored and result in broken links.
* Requiring explicit ``<br />\n`` sequences in ``<pre>`` elements in order to preserve linebreaks.

The workarounds we have in place for this are described further in the :py:meth:`~.JiveContent.jiveize_etree` method.

In addition, while Jive will happily accept a full HTML document as input, it appears to discard everything outside of the ``<body>`` tag, including CSS. As a workaround for this, the :py:meth:`~.JiveContent.inline_css_etree` method calls out to the `premailer <https://github.com/peterbe/premailer>`_ library to convert all embedded CSS to inline CSS on the elements themselves.
