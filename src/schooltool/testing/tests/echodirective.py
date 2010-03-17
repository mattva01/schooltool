from zope.interface import Interface
from zope import schema
from zope.configuration import fields


class IEcho(Interface):

    message = schema.Text(title=u"Message", required=False)

    echo_on_add = fields.Bool(
        title=u"Echo when parsing ZCML.", required=False,
        default=False)


def handle_echo(message):
    print 'Executing echo:', message


def echo(_context, message=None, echo_on_add=False):
    discriminator=('echo', message)
    if echo_on_add:
        print 'Adding ZCML action: %s' % repr(discriminator)
    _context.action(discriminator=discriminator,
                    callable=handle_echo,
                    args=(message,))

