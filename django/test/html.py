'''
Comparing two html documents.
'''
import re
from HTMLParser import HTMLParser, HTMLParseError


WHITESPACE = re.compile('\s+')


def normalize_whitespace(string):
    return WHITESPACE.sub(' ', string)


class Element(object):
    def __init__(self, name, attributes):
        self.name = name
        self.attributes = sorted(attributes)
        self.children = []
        self._pending_whitespace = ''

    def append(self, element):
        if isinstance(element, basestring):
            element = normalize_whitespace(element)
            if not self.children:
                element = element.lstrip()
            elif isinstance(self.children[-1], basestring):
                self.children[-1] += element
                self.children[-1] = normalize_whitespace(self.children[-1])
                return
        elif self.children:
            # removing last children if it is only whitespace
            # this can result in incorrect dom representations since
            # whitespace between inline tags like <span> is significant
            if isinstance(self.children[-1], basestring):
                if self.children[-1].isspace():
                    self.children.pop()
        if element:
            self.children.append(element)

    def finalize(self):
        def rstrip_last_element(children):
            if children:
                if isinstance(children[-1], basestring):
                    children[-1] = children[-1].rstrip()
                    if not children[-1]:
                        children.pop()
                        children = rstrip_last_element(children)
            return children

        rstrip_last_element(self.children)
        for child in self.children:
            if hasattr(child, 'finalize'):
                child.finalize()

    def __eq__(self, element):
        if self.name != element.name:
            return False
        if self.attributes != element.attributes:
            return False
        if self.children != element.children:
            return False
        return True

    def __ne__(self, element):
        return not self.__eq__(element)

    def __getitem__(self, key):
        return self.children[key]

    def __unicode__(self):
        output = u'<%s' % self.name
        for key, value in self.attributes:
            output += u' %s="%s"' % (key, value)
        if self.children:
            output += u'>\n'
            output += u''.join(unicode(c) for c in self.children)
            output += u'\n</%s>' % self.name
        else:
            output += u' />'
        return output

    def __str__(self):
        return str(unicode(self))

    def __repr__(self):
        return unicode(self)


class RootElement(Element):
    def __init__(self):
        super(RootElement, self).__init__(None, ())

    def __unicode__(self):
        return u''.join(unicode(c) for c in self.children)


class Parser(HTMLParser):
    SELF_CLOSING_TAGS = ('br' , 'hr', 'input', 'img', 'meta', 'spacer',
        'link', 'frame', 'base', 'col')

    def __init__(self):
        HTMLParser.__init__(self)
        self.root = RootElement()
        self.open_tags = []
        self.element_positions = {}

    def error(self, msg):
        raise HTMLParseError(msg, self.getpos())

    def format_position(self, position=None, element=None):
        if not position and element:
            position = self.element_positions[element]
        if position is None:
            position = self.getpos()
        if hasattr(position, 'lineno'):
            position = position.lineno, position.offset
        return 'Line %d, Column %d' % position

    @property
    def current(self):
        if self.open_tags:
            return self.open_tags[-1]
        else:
            return self.root

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.SELF_CLOSING_TAGS:
            self.handle_endtag(tag)

    def handle_starttag(self, tag, attrs):
        element = Element(tag, attrs)
        self.current.append(element)
        if tag not in self.SELF_CLOSING_TAGS:
            self.open_tags.append(element)
        self.element_positions[element] = self.getpos()

    def handle_endtag(self, tag):
        if not self.open_tags:
            self.error("Unexpected end tag `%s` (%s)" % (
                tag, self.format_position()))
        element = self.open_tags.pop()
        while element.name != tag:
            if not self.open_tags:
                self.error("Unexpected end tag `%s` (%s)" % (
                    tag, self.format_position()))
            element = self.open_tags.pop()

    def handle_data(self, data):
        self.current.append(data)

    def handle_charref(self, name):
        self.current.append('&%s;' % name)

    def handle_entityref(self, name):
        self.current.append('&%s;' % name)


def parse_html(html):
    parser = Parser()
    parser.feed(html)
    parser.close()
    document = parser.root
    document.finalize()
    # Removing ROOT element if it's not necessary
    if len(document.children) == 1:
        document = document.children[0]
    return document
