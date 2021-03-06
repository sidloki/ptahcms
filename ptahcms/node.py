""" Node implementation """
import sqlalchemy as sa
from collections import OrderedDict
from pyramid.compat import text_type
from zope.interface import implementer

import ptah
from ptahcms import action
from ptahcms.permissions import View
from ptahcms.interfaces import NotFound, Forbidden
from ptahcms.interfaces import INode, IApplicationPolicy


@implementer(INode,
             ptah.IACLsAware,
             ptah.IOwnersAware,
             ptah.ILocalRolesAware)

class Node(ptah.get_base()):
    """ Base class for persistent objects.

    .. attribute:: __uri__

       Unique object id. **Required**

    .. attribute:: __type__

       Type information object :py:class:`ptahcms.TypeInformation`

    .. attribute:: __parent__

       Parent of node. Ptah doesn't load `__parent__` automatically.
       To load node parents use :py:func:`ptahcms.load_parents` function.

    .. attribute:: __owner__

       URI of owner principal. It possible to load principal object
       by using :py:func:`ptah.resolve` function.

    .. attribute:: __local_roles__

       :py:class:`ptah.JsonDictType` which contains a principal uri as a
       key and a sequence of role's granted to principal for Node.

    .. attribute:: __acls__

       a :py:class:`ptah.JsonListType` of :py:class:`ptah.ACL` strings
       registered with security machinery.

    .. attribute:: __annotations__

       a dictionary which contains strings arbitrary annotations data.

    .. attribute:: __uri_factory__

       function which will return value for __uri__.  the uri must be
       resolvable by using :py:func:`ptah.resolve` function.

    """

    __tablename__ = 'ptahcms_nodes'

    __id__ = sa.Column('id', sa.Integer, primary_key=True)
    __type_id__ = sa.Column('type', sa.String(128), info={'uri':True})
    __type__ = None

    __uri__ = sa.Column('uri', sa.String(255), unique=True,
                        nullable=False, info={'uri':True})
    __parent_uri__ = sa.Column('parent', sa.String(255),
                               sa.ForeignKey(__uri__), info={'uri': True})

    __owner__ = sa.Column('owner', sa.String(255), default='',info={'uri':True})
    __local_roles__ = sa.Column('roles', ptah.JsonDictType(), default={})
    __acls__ = sa.Column('acls', ptah.JsonListType(), default=[])
    __annotations__ = sa.Column('annotations', ptah.JsonDictType(),default={})

    __children__ = sa.orm.relationship(
        'Node', backref=sa.orm.backref('__parent_ref__', remote_side=[__uri__]),
        cascade='all', lazy='joined', join_depth=1)

    __mapper_args__ = {'polymorphic_on': __type_id__, 'with_polymorphic': '*'}

    __parent__ = None
    __uri_factory__ = None

    __acl__ = ptah.ACLsProperty()

    def __init__(self, **kw):
        self.__owners__ = []
        self.__local_roles__ = {}
        self.__permissions__ = []

        for attr, value in kw.items():
            setattr(self, attr, value)

        if '__parent__' in kw and kw['__parent__'] is not None:
            self.__parent_uri__ = kw['__parent__'].__uri__

        try:
            self.__uri__ = self.__uri_factory__()
        except TypeError:
            raise TypeError(
                'Subclass of Node has to override __uri_factory__')

    @action(permission=View)
    def info(self):
        info = OrderedDict(
            (('__type__', self.__type_id__),
             ('__content__', False),
             ('__uri__', self.__uri__),
             ('__parents__', [p.__uri__ for p in load_parents(self)]),
             ))

        return info

    def get_session(self):
        return sa.orm.object_session(self)


def load(uri, permission=None):
    """ Load node by `uri` and initialize __parent__ attributes. Also checks
    permission if permissin is specified.

    :param uri: Node uri
    :param permission: Check permission on node object
    :type permission: Permission id or None
    :raise KeyError: Node with this uri is not found.
    :raise Forbidden: If current principal doesn't pass permission check on loaded node.
    """
    item = ptah.resolve(uri)

    if item is not None:
        load_parents(item)

        if permission is not None:
            if not ptah.check_permission(permission, item):
                raise Forbidden()
    else:
        raise NotFound(uri)

    return item


def load_parents(node):
    """ Load and initialize `__parent__` attribute for node.
    Returns list of loaded parents.

    :param node: ptahcms.Node node
    """
    parents = []
    parent = node
    while parent is not None:
        if not isinstance(parent, Node):
            break

        if parent.__parent__ is None:
            parent.__parent__ = parent.__parent_ref__

        parent = parent.__parent__
        if parent is not None:
            parents.append(parent)

    root = node if not parents else parents[-1]
    if not IApplicationPolicy.providedBy(root):
        try:
            root.__parent__ = get_policy()
        except AttributeError:
            # __parent__ is read onl
            pass

    return [p for p in parents if isinstance(p, Node)]


KEY = '__ptahcms_policy__'

def get_policy():
    """ Get current policy """
    return ptah.tldata.get(KEY)

def set_policy(policy):
    """ Set current policy """
    return ptah.tldata.set(KEY, policy)
