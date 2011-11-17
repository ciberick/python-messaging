"""
============================================
Message - abstraction of a message
============================================

SYNOPSIS
--------

Example:

  importing messaging.message as message

  # constructor + setters
  msg = message.Message();
  msg.body = "hello world";
  msg.header = {"subject" : "test"}
  msg.header["message-id"] = "123"

  # fancy constructor
  msg = message.Message(
      body = "hello world",
      header = {
          "subject" : "test",
          "message-id" : "123",
      },
  )

  # getters
  if (msg.body) {
      ...
  }
  id = msg.header["message-id"]

===========
DESCRIPTION
===========

This module provides an abstraction of a "message", as used in
messaging, see for instance:
http://en.wikipedia.org/wiki/Enterprise_messaging_system.

A message consists of header fields (collectively called "the header
of the message") and a body.

Each header field is a key/value pair where the key and the value are
text strings. The key is unique within the header so we can use a dict
to represent the header of the message.

The body is either a text string or a binary string. This distinction
is needed because text may need to be encoded (for instance using
UTF-8) before being stored on disk or sent across the network.

To make things clear:

- a *text string* (aka *character string*) is a sequence of Unicode characters

- a *binary string* (aka *byte string*) is a sequence of bytes

Both the header and the body can be empty.

============
JSON MAPPING
============

In order to ease message manipulation (e.g. exchanging between
applications, maybe written in different programming languages), we
define here a standard mapping between a Message object and a JSON object.

A message as defined above naturally maps to a JSON object with the
following fields:

header
    the message header as a JSON object (with all values being JSON
    strings)

body
    the message body as a JSON string

text
    a JSON boolean specifying whether the body is text string (as opposed
    to binary string) or not

encoding
    a JSON string describing how the body has been encoded (see below)

All fields are optional and default to empty/false if not present.

Since JSON strings are text strings (they can contain any Unicode
character), the message header directly maps to a JSON object. There
is no need to use encoding here.

For the message body, this is more complex. A text body can be put
as-is in the JSON object but a binary body must be encoded beforehand
because JSON does not handle binary strings. Additionally, we want to
allow body compression in order to optionally save space. This is
where the encoding field comes into play.

The encoding field describes which transformations have been applied
to the message body. It is a *+* separated list of transformations
that can be:

base64
    Base64 encoding (for binary body or compressed body)

utf8
    UTF-8 encoding (only needed for a compressed text body)

zlib
    Zlib compression

Here is for instance the JSON object representing an empty message
(i.e. the result of Message()):

  {}

Here is a more complex example, with a binary body:

  {
    "header":{"subject":"demo","destination":"/topic/test"},
    "body":"YWJj7g==",
    "encoding":"base64"
  }

You can use the jsonify() method to convert a Message object into a
dict representing the equivalent JSON object.

Conversely, you can create a new Message object from a compatible
JSON object (again, a dict) with the dejsonify() method.

Using this JSON mapping of messages is very convenient because you can
easily put messages in larger JSON data structures. You can for
instance store several messages together using a JSON array of these
messages.

Here is for instance how you could construct a message containing in
its body another message along with error information:

  try:
      import simplejson as json
  except ImportError:
      import json
  import time
  # get a message from somewhere...
  msg1 = ...
  # jsonify it and put it into a simple structure
  body = {
      "message" : msg1.jsonify(),
      "error"   : "an error message",
      "time"    : time.time(),
  }
  # create a new message with this body
  msg2 = message.Message(body = json.dumps($body));
  msg2.header["content-type"] = "message/error"

A receiver of such a message can easily decode it:

  try:
      import simplejson as json
  except ImportError:
      import json
  # get a message from somewhere...
  msg2 = ...
  # extract the body which is a JSON object
  body = json.loads(msg2.body)
  # extract the inner message
  msg1 = message.dejsonify(body['message'])

=================================
STRINGIFICATION AND SERIALIZATION
=================================

In addition to the JSON mapping described above, we also define how to
stringify and serialize a message.

A *stringified message* is the string representing its equivalent
JSON object. A stringified message is a text string and can for
instance be used in another message. See the stringify() and
destringify() methods.

A *serialized message* is the UTF-8 encoding of its stringified
representation. A serialized message is a binary string and can for
instance be stored in a file. See the serialize() and deserialize()
methods.

For instance, here are the steps needed in order to store a message
into a file:

# transform the programming language specific abstraction of the message
into a JSON object
# transform the JSON object into its (text) string representing
# transform the JSON text string into a binary string using UTF-8
encoding


"1" is called *jsonify*, "1 + 2" is called *stringify* and "1 + 2 +
3" is called *serialize*.

To sum up:

            Message object
                 |  ^
       jsonify() |  | dejsonify()
                 v  |
          JSON compatible dict
                 |  ^
     JSON encode |  | JSON decode
                 v  |
             text string
                 |  ^
    UTF-8 encode |  | UTF-8 decode
                 v  |
            binary string

"""
__version__ = "$Revision: 1 $"
# $Source$

import base64
import copy
try:
    import hashlib
    md5_hash = hashlib.md5
except ImportError:
    import md5
    md5_hash = md5.md5
try:
    import simplejson as json
except ImportError:
    import json
import sys
import zlib

DEFAULT_BODY = ''.encode()

def is_ascii(string):
    """ Returns True is the string is ascii. """
    try:
        if is_bytes(string):
            string = string.decode()
        string.encode("ascii")
    except UnicodeDecodeError:
        return False
    except UnicodeEncodeError:
        return False
    return True

def is_bytes(string):
    """ Check if given string is a byte string. """
    try:
        if isinstance(string, bytes): # python 3
            return True
        else:
            return False
    except NameError:
        if isinstance(string, unicode):
            return False
        else:
            return True

def dejsonify(obj):
    """ Returns a message from json structure. """
    if not isinstance(obj, dict):
        raise ValueError("expecting a json object: %s" % obj)
    is_text = False
    if obj.get('text'):
        is_text = True
    header = obj.get('header', dict())
    body = obj.get('body', DEFAULT_BODY)
    encoding = dict()
    if obj.get('encoding'):
        encoding = obj['encoding'].split('+')
        if not is_bytes(body):
            body = body.encode()
    if 'base64' in encoding:
        body = base64.b64decode(body)
    if 'zlib' in encoding:
        body = zlib.decompress(body)
    if 'utf8' in encoding:
        body = body.decode('utf-8')
    if is_bytes(body):
        if is_text:
            body = body.decode()
    else:
        if not is_text:
            body = body.encode()
    return Message(body, header)
    
def destringify(string):
    """ Destringify the given message. """
    try:
        jsonified = json.loads(string)
    except ValueError:
        error = sys.exc_info()[1]
        raise ValueError("not a valid json string provided: %s" % error)
    return dejsonify(jsonified)
    
def deserialize(binary):
    """ Deserialize a message. """
    decoded = binary
    try:
        if is_bytes(decoded):
            decoded = decoded.decode('utf-8')
    except UnicodeDecodeError:
        error = sys.exc_info()[1]
        raise ValueError("not a valid binary string %s: %s" 
                         % (binary, error))
    return destringify(decoded)

class Message(object):
    """A Message abstraction class. """
    
    def __init__(self, body=DEFAULT_BODY, header=dict()):
        """ Initialize the object """
        self.body = body
        self.header = header
        self.text = not is_bytes(body)
        
    def get_body(self):
        """ Returns the body of the message. """
        return self.__body
    
    def set_body(self, value):
        """ Set the message body to new value. """
        if value is None:
            value = DEFAULT_BODY
        self.__body = value
        self.text = not is_bytes(value)
    body = property(get_body, set_body)
    
    def get_header(self):
        """ Return the header of the message. """
        return self.__header
    
    def set_header(self, value):
        """ Set the message header to new value. """
        if value is None:
            value = dict()
        self.__header = value
    header = property(get_header, set_header)
    
    def get_text(self):
        """ Is it a text message? """
        if self.body is None:
            return False
        return self.__text
    
    def is_text(self):
        """ Is it a text message? """
        return self.get_text()
    
    def set_text(self, value):
        """ Set if the message is text. """
        self.__text = value
    text = property(get_text, set_text)
        
    def jsonify(self, option=dict()):
        """ Transforms the message to JSON. """
        compression = option.get('compression')
        if compression is not None and compression != 'zlib':
            raise ValueError("unsupported compression type: %s" 
                             % compression)
        obj = dict()
        if self.header:
            obj['header'] = self.header
        obj['body'] = self.body
        if self.text:
            obj['text'] = True
            if compression:
                obj['encoding'] = dict()
                obj['body'] = obj['body'].encode("utf-8")
                obj['encoding'] = {'utf8' : True}
                if compression == "zlib":
                    tmp = zlib.compress(obj['body'])
                    if (len(tmp) / len(obj['body'])) < 0.9:
                        obj['body'] = tmp
                        obj['encoding']["zlib"] = True
                if obj.get('encoding') and obj['encoding'].get('zlib'):
                    obj['body'] = base64.b64encode(obj['body'])
                    obj['encoding']['base64'] = True
                else:
                    obj['body'] = self.body
                    del(obj['encoding'])
        elif self.body:
            if compression == "zlib":
                obj['encoding'] = dict()
                tmp = zlib.compress(obj['body'])
                if (len(tmp) / len(obj['body'])) < 0.9:
                    obj['body'] = tmp
                    obj['encoding']["zlib"] = True
            if not is_ascii(obj['body']):
                if obj.get('encoding') is None:
                    obj['encoding'] = dict()
                obj['body'] = base64.b64encode(obj['body'])
                obj['encoding']['base64'] = True
        if obj.get('encoding'):
            obj['encoding'] = '+'.join(obj['encoding'].keys())
        return obj
        
    def stringify(self, option=dict()):
        """ Transforms the message to string. """
        jsonified = self.jsonify(option)
        if is_bytes(jsonified.get('body')):
            jsonified['body'] = jsonified.get('body', '').decode('utf-8')
        return json.dumps(jsonified)
    
    def serialize(self, option=dict()):
        """ Serialize message. """
        stringified = self.stringify(option)
        return stringified.encode('utf-8')
    
    def __repr__(self):
        return self.stringify()
    
    def size(self):
        """ Returns an approximation of the message size. """
        size = len(self.body) + 1
        size += sum([len(key) + len (value) + 2
                     for (key, value) in self.header.items()])
        return size
        
    def clone(self):
        """ Returns a clone of the message. """
        return copy.deepcopy(self)
    
    def md5(self):
        """ Return the checksum of the message. """
        header_c = ''.join(["%s:%s\n" % (key, self.header[key]) 
                              for key in sorted(self.header.keys())])
        header_c = md5_hash(header_c.encode('utf-8')).hexdigest()
        if self.is_text():
            body_c = md5_hash(self.body.encode('utf-8')).hexdigest()
        else:
            body_c = md5_hash(self.body).hexdigest()
        composed = "%d%s%s" % (self.is_text(), header_c, body_c)
        return md5_hash(composed.encode('utf-8')).hexdigest()
    
    def __eq__(self, other):
        """ Check if the message is equal to the given one. """
        if not isinstance(other, Message):
            return False
        if self.text != other.text or self.body != other.body:
            return False
        if self.header is not None:
            if other.header is None:
                return False
            for (key, value) in self.header.items():
                if value != other.header.get(key):
                    return False
        else:
            return self.header == other.header
        return True
    
    def equals(self, other):
        """ Check if the message is equal to the given one. """
        return self.__eq__(other)
