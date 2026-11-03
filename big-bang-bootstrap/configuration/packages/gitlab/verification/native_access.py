"""Verify selected GitLab GET evidence. No account or membership mutation.

Callers must fetch exact UID/group endpoints with private credentials and trusted
TLS. This guard does not prove session/token revocation or provider MFA timing.
"""
def verify(expected, user, group, direct, effective, operation):
    if operation not in ('enrolled','removed'):
        raise ValueError('unknown verification operation')
    for key in ('user_id','group_id'):
        if type(expected.get(key)) is not int or expected[key] <= 0:
            raise ValueError('explicit positive numeric identities required')
    if expected.get('provider') != 'openid_connect' or not expected.get('subject'):
        raise ValueError('exact provider and stable subject required')
    import re
    path=expected.get('group_path','')
    if not isinstance(path,str) or not re.fullmatch(r'tenants/[a-z][a-z0-9-]{0,62}',path):
        raise ValueError('exact private tenant group required')
    if expected.get('access_level') not in (20,30,40,50):
        raise ValueError('unsupported native tenant role')
    if type(user.get('id')) is not int or user.get('id') != expected['user_id'] or user.get('is_admin') is not False:
        raise ValueError('wrong user or instance-admin authority')
    identities=[x for x in user.get('identities',[]) if x.get('provider')==expected['provider']]
    if len(identities)!=1 or identities[0].get('extern_uid') != expected['subject']:
        raise ValueError('provider subject mismatch; never substitute email matching')
    if type(group.get('id')) is not int or group.get('id') != expected['group_id'] or group.get('full_path') != path or group.get('visibility') != 'private':
        raise ValueError('wrong or nonprivate tenant group')
    if operation=='removed':
        if direct is not None or effective is not None:
            raise ValueError('direct or inherited group access remains')
        return {'group_membership_absent':True,'independent_credentials_revoked':False}
    if user.get('state')!='active':
        raise ValueError('account has not been explicitly approved')
    for member in (direct,effective):
        if not isinstance(member,dict) or type(member.get('id')) is not int or type(member.get('access_level')) is not int or member.get('id')!=expected['user_id'] or member.get('access_level')!=expected['access_level']:
            raise ValueError('unexpected direct or inherited effective role')
    return {'native_group_access_verified':True,'other_groups_or_projects_verified':False}
