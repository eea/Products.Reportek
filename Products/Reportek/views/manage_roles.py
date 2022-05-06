from base_admin import BaseAdmin
from operator import itemgetter
from Products.Reportek.constants import ENGINE_ID, ECAS_ID
from Products.Reportek.config import REPORTEK_DEPLOYMENT, DEPLOYMENT_BDR
from Products.Reportek.catalog import searchResults
from Products.Reportek.rabbitmq import queue_msg


class ManageRoles(BaseAdmin):

    def __call__(self, *args, **kwargs):
        super(ManageRoles, self).__call__(*args, **kwargs)
        if self.__name__ == 'assign_role':
            if self.request.get('btn.assign'):
                self.assign_role()

        elif self.__name__ == 'revoke_roles':
            if self.request.get('btn.revoke'):
                self.revoke_roles()

        elif self.__name__ == 'disabled_members':
            if self.request.get('btn.bulkrevoke'):
                self.bulk_revoke_roles()

        return self.index()

    def get_all_country_codes(self):
        return [c.get('iso') for c in self.localities_rod]

    def get_user_localroles(self, username):
        results = []
        for brain in searchResults(self.context.Catalog,
                                   dict(meta_type='Report Collection')):
            coll = brain.getObject()
            local_roles = coll.get_local_roles_for_userid(username)
            if local_roles:
                results.append({
                    'country': coll.getCountryName,
                    'collection': coll,
                    'roles': ', '.join([role for role in local_roles])
                })

        return results

    def assign_role(self):
        collections = self.request.get('collections', [])
        role = self.request.get('role', '')

        if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
            if role == 'Reporter (Owner)':
                role = 'Owner'

        search_type = self.request.get('search_type')
        entity = self.request.get('username', '')
        match_groups = []
        groups = False

        results = []

        if search_type == 'groups':
            entity = self.request.get('groupsname', '')
            use_subgroups = self.request.get('use-subgroups')
            if use_subgroups:
                match_groups = use_subgroups.split(',')
                groups = True

        for collection in collections:
            cur_entity = entity
            path, matched = collection.split(',')
            obj = self.context.unrestrictedTraverse(path)

            if groups and (matched in match_groups):
                cur_entity = matched
            elif groups and not (matched in match_groups):
                continue

            roles = set(obj.get_local_roles_for_userid(cur_entity))
            roles.add(role)
            obj.manage_setLocalRoles(cur_entity, list(roles))
            obj.reindex_object()
            # Sync role assignment to associated transfers folder
            if path in self.request.get('sync_transfers', []):
                transfer_path = '/'.join(['/transfers'] + path.split('/')[1:])
                transfer = self.context.unrestrictedTraverse(transfer_path,
                                                             None)
                if transfer:
                    t_roles = set(
                        transfer.get_local_roles_for_userid(cur_entity))
                    t_roles.add(role)
                    transfer.manage_setLocalRoles(cur_entity, list(t_roles))
                    results.append({
                        'entity': cur_entity,
                        'path': transfer_path,
                        'url': transfer.absolute_url(),
                        'role': role
                    })
            results.append({
                'entity': cur_entity,
                'path': path,
                'url': obj.absolute_url(),
                'role': role
            })

        if results:
            results.sort(key=itemgetter('path'))
            # notify role adding
            engine = self.context.unrestrictedTraverse(ENGINE_ID, None)
            if getattr(engine, 'col_role_sync_rmq', False):
                for url in [res.get('url') for res in results]:
                    # TODO: add host info to path before publishing
                    queue_msg(url,
                              queue="collections_sync")
            self.request['search_term'] = ''
        self.request['op_results'] = results

    def revoke_roles(self):
        collections = self.request.get('collections', [])
        search_type = self.request.get('search_type')
        entity = self.request.get('username', '')
        role = self.request.get('role', '')
        match_groups = []
        results = []
        sync_transfers = False

        if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
            sync_transfers = True
            if role == 'Reporter (Owner)':
                role = 'Owner'

        if search_type == 'groups':
            entity = self.request.get('groupsname', '')
            use_subgroups = self.request.get('use-subgroups', '')
            match_groups = use_subgroups.split(',')

        for collection in collections:
            path, matched = collection.split(',')
            obj = self.context.unrestrictedTraverse(path)

            if match_groups and matched:
                if matched in match_groups:
                    entity = matched

            revoke_roles = self.request.get(path.replace('/', '_'), [])
            if not isinstance(revoke_roles, list):
                revoke_roles = [revoke_roles]
            roles = set(obj.get_local_roles_for_userid(entity))
            for r in revoke_roles:
                if (REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR
                        and r == 'Reporter (Owner)'):
                    roles.remove('Owner')
                else:
                    roles.remove(r)
            obj.manage_delLocalRoles([entity])
            if roles:
                obj.manage_setLocalRoles(entity, list(roles))
            obj.reindex_object()
            # Remove certain roles from transfer folders
            if sync_transfers:
                transfer_path = '/'.join(['/transfers'] + path.split('/')[1:])
                transfer = self.context.unrestrictedTraverse(transfer_path,
                                                             None)
                removed = False
                if transfer:
                    t_roles = set(transfer.get_local_roles_for_userid(entity))
                    revocable = [r for r in revoke_roles
                                 if r in ['ClientFG',
                                          'ClientODS',
                                          'ClientCARS',
                                          'ClientHDV']]
                    for role in revocable:
                        if role in t_roles:
                            t_roles.remove(role)
                            removed = True
                    transfer.manage_delLocalRoles([entity])
                    if t_roles:
                        transfer.manage_setLocalRoles(entity, list(t_roles))
                    if removed:
                        results.append({
                            'entity': entity,
                            'path': transfer_path,
                            'url': transfer.absolute_url(),
                            'role': role
                        })
            results.append({
                'entity': entity,
                'path': path,
                'url': obj.absolute_url(),
                'role': role
            })

        if results:
            engine = self.context.unrestrictedTraverse(ENGINE_ID, None)
            if getattr(engine, 'col_role_sync_rmq', False):
                for url in [res.get('url') for res in results]:
                    queue_msg(url,
                              queue="collections_sync")

            results.sort(key=itemgetter('path'))
            self.request['search_term'] = ''
        self.request['op_results'] = results

    def search_ldap_users(self, term):
        params = [name for name, value in self.get_ldap_schema()]
        acl_users = self.get_acl_users()

        users = [acl_users.findUser(search_param=p, search_term=term)
                 for p in params]
        users = reduce(lambda x, y: x + y, users)  # noqa: F821
        users = {user.get('uid'): user for user in users}.values()

        return users

    def search_ecas_users(self, term):
        ecas_path = '/' + ENGINE_ID + '/acl_users/' + ECAS_ID
        ecas = self.context.unrestrictedTraverse(ecas_path, None)
        ecas_db = getattr(ecas, '_ecas_id', None)
        users = []
        if ecas_db:
            for user in ecas_db.values():
                username = user.username
                email = user.email
                if isinstance(username, unicode):  # noqa: F821
                    username = username.encode('utf-8')
                if isinstance(email, unicode):  # noqa: F821
                    email = email.encode('utf-8')
                if username:
                    if isinstance(username, unicode):  # noqa: F821
                        username = username.encode('utf-8')
                    if term in username:
                        result = {
                            'uid': username,
                            'mail': email
                        }
                        users.append(result)
                        continue
                if email:
                    if term in email:
                        entity = username
                        if not entity:
                            entity = email
                        result = {
                            'uid': entity,
                            'mail': email
                        }
                        users.append(result)

        return users

    def search_entities(self):
        term = self.request.get('search_term')
        s_type = self.request.get('search_type')
        response = {}
        if term:
            if s_type == 'groups':
                groups = self.search_ldap_groups(term)
                response['groups'] = groups
            else:
                ldap_users = self.search_ldap_users(term)
                ecas_users = []
                if REPORTEK_DEPLOYMENT == DEPLOYMENT_BDR:
                    ecas_users = self.search_ecas_users(term)

                if ldap_users:
                    err_users = [user for user in ldap_users
                                 if user.get('sn') == 'Error']
                    if err_users:
                        response['errors'] = True

                users = ecas_users + ldap_users

                if users:
                    try:
                        users.sort(key=itemgetter('uid'))
                    except KeyError:
                        # Fail silently if missing 'uid'
                        pass

                response['users'] = users

        return response

    def get_ldap_schema(self):
        return (self.get_acl_users()
                    .getLDAPSchema())

    def display_confirmation(self):
        return ((self.request.get('username', None) or
                 self.request.get('groupsname', None)) and
                self.request.get('role', None))

    def get_assigned_disabled_members(self):
        disabled_uids = []
        query = {'meta_type': ['Report Collection']}
        result = {}
        acl_users = self.get_acl_users()
        disabled_users = acl_users.findUser(search_param='employeeType',
                                            search_term='disabled',
                                            exact_match='1')
        disabled_uids = [user.get('uid') for user in disabled_users]
        groups = acl_users.getGroups()
        groups = [group[0] for group in groups]
        group_prefixes = tuple({group.split('-')[0] for group in groups})

        brains = searchResults(self.context.Catalog, query)
        for brain in brains:
            local_defined_users = brain.local_defined_users
            if local_defined_users:
                for entity in local_defined_users:
                    entry = (brain.getPath(),
                             brain.local_defined_roles.get(entity))
                    if entity in disabled_uids:
                        if entity not in result:
                            result[entity] = {
                                "type": "User",
                                "paths": [entry]
                            }
                        else:
                            result[entity]['paths'].append(entry)
                    elif entity.startswith(group_prefixes):
                        if entity not in groups:
                            if entity not in result:
                                result[entity] = {
                                    "type": "Group",
                                    "paths": [entry]
                                }
                            else:
                                result[entity]['paths'].append(entry)
                    if result.get(entity):
                        result[entity]['paths'].sort(key=itemgetter(0))

        return result

    def bulk_revoke_roles(self):
        members = self.request.get('members', [])
        results = []
        for member in members:
            colls = self.request.get(member).split(',')
            for path in colls:
                obj = self.context.unrestrictedTraverse(path)
                obj.manage_delLocalRoles([member])
                obj.reindex_object()
                results.append({
                    'entity': member,
                    'path': path,
                })

        if results:
            results.sort(key=itemgetter('path'))
        self.request['op_results'] = results
