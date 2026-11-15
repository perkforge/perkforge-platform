"""Synthetic HTTPS authority and reconciliation acceptance tests."""
import copy
from security import test_mattermost_context as fixture
ROOT, T, C, U = (fixture.ROOT, fixture.T, fixture.C, fixture.U)

class MattermostMembership(fixture.MattermostFixture):

    def setUp(self):
        fixture.MattermostFixture.setUp(self)
        self.play = ROOT / 'big-bang-bootstrap/configuration/authorization/sso/mattermost/context/plan.yaml'
        self.v.update(mattermost_membership_plan=True, mattermost_keycloak_origin=self.origin, mattermost_keycloak_token_file=str(self.d / 'token'), mattermost_keycloak_ca_file=str(self.d / 'ca'))
        self.contract.update(groups=[dict(id=r, path='/tenants/portal/' + r) for r in ['admins', 'developers', 'viewers']], bindings=[dict(subject='subject-one', user_id=U)], exceptions=[])
        self.contract['groups'].append(dict(id='engineers', path='/platform/engineers'))
        self.s['extra_paths'] = {f'/api/v4/users/{U}': dict(id=U, delete_at=0, auth_service='openid', auth_data='subject-one', roles='system_user')}
        for g in self.contract['groups']:
            self.s['extra_paths'][f"/admin/realms/perkforge/groups/{g['id']}"] = dict(g, subGroupCount=0, subGroups=[])
            self.s['extra_paths'][f"/admin/realms/perkforge/groups/{g['id']}/members?first=0&max=200&briefRepresentation=false"] = []
        self.members_path = '/admin/realms/perkforge/groups/viewers/members?first=0&max=200&briefRepresentation=false'
        self.s['extra_paths'][self.members_path] = [dict(id='subject-one', enabled=True)]

    def test_default_and_check(self):
        self.run_play(dict(mattermost_membership_plan=False, mattermost_keycloak_token_file='/missing'))
        self.run_play(dict(mattermost_keycloak_token_file='/missing'), check=True)
        self.assertEqual(self.s['calls'], [])

    def test_exact_and_manual_drift(self):
        self.assertIn('0 additions, 0 removals', self.run_play().stdout)
        self.s['channel_members'] = [dict(channel_id=C, user_id='x' * 26, roles='channel_user')]
        self.assertIn('1 additions, 1 removals', self.run_play().stdout)
        self.assertIn('changed=0', self.run_play().stdout)

    def test_authoritative_empty_and_exception(self):
        self.s['extra_paths'][self.members_path] = []
        self.assertIn('0 additions, 1 removals', self.run_play().stdout)
        self.contract['exceptions'] = [U]
        self.assertIn('0 additions, 0 removals', self.run_play().stdout)

    def test_incomplete_unresolved_foreign_authority(self):
        original = copy.deepcopy(self.s['extra_paths'])
        for value in [[dict(id='subject-one', enabled=True)] * 200, [dict(id='unresolved', enabled=True)], {}]:
            self.s['extra_paths'] = copy.deepcopy(original)
            self.s['extra_paths'][self.members_path] = value
            self.run_play(success=False)
        self.s['extra_paths'] = copy.deepcopy(original)
        self.s['extra_paths']['/admin/realms/perkforge/groups/admins']['path'] = '/tenants/other/admins'
        self.run_play(success=False)

    def test_immutable_link_denial(self):
        for field, value in [('auth_service', 'email'), ('auth_data', 'other-subject'), ('delete_at', 1), ('roles', 'system_user system_admin')]:
            self.s['extra_paths'][f'/api/v4/users/{U}'] = dict(id=U, delete_at=0, auth_service='openid', auth_data='subject-one', roles='system_user') | {field: value}
            self.run_play(success=False)

    def test_apply_and_idempotence(self):
        self.s['apply_fixture'] = True
        self.s['channel_members'] = [dict(channel_id=C, user_id='x' * 26, roles='channel_user')]
        approved = dict(mattermost_membership_apply=True, mattermost_membership_apply_confirmed=True, mattermost_invitation_boundary_verified=True, mattermost_membership_approved_add=[U], mattermost_membership_approved_remove=['x' * 26])
        self.run_play(approved)
        self.assertEqual([m['user_id'] for m in self.s['channel_members']], [U])
        self.s['calls'] = []
        self.run_play(approved | dict(mattermost_membership_approved_add=[], mattermost_membership_approved_remove=[]))
        self.assertTrue(all((m == 'GET' for m, _ in self.s['calls'])))

    def test_apply_without_confirmation_denied(self):
        self.run_play(dict(mattermost_membership_apply=True), success=False)
        self.assertTrue(all((m == 'GET' for m, _ in self.s['calls'])))

    def test_subgroup_completeness_required(self):
        group = self.s['extra_paths']['/admin/realms/perkforge/groups/admins']
        for bad in ['garbage', None, 1]:
            group['subGroupCount'] = bad
            self.run_play(success=False)
        del group['subGroupCount']
        self.run_play(success=False)

    def test_native_admin_role_is_not_inferred(self):
        self.s['channel_members'][0]['roles']='channel_user channel_admin'
        self.run_play(success=False)

    def test_pe_group_is_authoritative(self):
        self.s['extra_paths'][self.members_path]=[]
        self.s['extra_paths']['/admin/realms/perkforge/groups/engineers/members?first=0&max=200&briefRepresentation=false']=[dict(id='subject-one',enabled=True)]
        self.assertIn('0 additions, 0 removals',self.run_play().stdout)

    def test_native_team_admin_denied(self):
        self.s['team_members'][0]['roles']='team_user team_admin'
        self.run_play(success=False)

    def test_elevation_during_apply_is_not_success(self):
        self.s['apply_fixture']=True
        self.s['elevate_after_add']=True
        self.s['channel_members']=[]
        self.run_play(dict(mattermost_membership_apply=True,
                           mattermost_membership_apply_confirmed=True,
                           mattermost_invitation_boundary_verified=True,
                           mattermost_membership_approved_add=[U],
                           mattermost_membership_approved_remove=[]),success=False)

    def test_authority_drift_before_apply_causes_no_mutations(self):
        self.s['apply_fixture'] = True
        self.s['channel_members'] = []
        self.s['response_sequences'] = {self.members_path: [[dict(id='subject-one', enabled=True)], []]}
        self.run_play(dict(mattermost_membership_apply=True,
                           mattermost_membership_apply_confirmed=True,
                           mattermost_invitation_boundary_verified=True,
                           mattermost_membership_approved_add=[U],
                           mattermost_membership_approved_remove=[]), success=False)
        self.assertTrue(all(method == 'GET' for method, _ in self.s['calls']))
        self.assertEqual(self.s['channel_members'], [])

    def test_failed_add_preserves_removal_then_fresh_retry(self):
        self.s['apply_fixture'] = True
        self.s['fail_membership_add'] = True
        foreign = 'x' * 26
        self.s['channel_members'] = [dict(channel_id=C, user_id=foreign, roles='channel_user')]
        approved = dict(mattermost_membership_apply=True,
                        mattermost_membership_apply_confirmed=True,
                        mattermost_invitation_boundary_verified=True,
                        mattermost_membership_approved_add=[U],
                        mattermost_membership_approved_remove=[foreign])
        self.run_play(approved, success=False)
        self.assertEqual(self.s['channel_members'], [])
        mutations = [(method, path) for method, path in self.s['calls'] if method != 'GET']
        self.assertEqual(mutations, [('DELETE', f'/api/v4/channels/{C}/members/{foreign}'),
                                    ('POST', f'/api/v4/channels/{C}/members')])
        self.s['fail_membership_add'] = False
        self.s['calls'] = []
        # Stale approval lists cannot silently apply a now-different delta.
        self.run_play(approved, success=False)
        self.assertTrue(all(method == 'GET' for method, _ in self.s['calls']))
        self.s['calls'] = []
        self.run_play(approved | dict(mattermost_membership_approved_remove=[]))
        self.assertEqual([member['user_id'] for member in self.s['channel_members']], [U])
        self.assertFalse(any(method == 'DELETE' for method, _ in self.s['calls']))

    def test_overlapping_authority_retains_member_until_last_group_removed(self):
        admin_path = '/admin/realms/perkforge/groups/admins/members?first=0&max=200&briefRepresentation=false'
        self.s['extra_paths'][admin_path] = [dict(id='subject-one', enabled=True)]
        self.assertIn('0 additions, 0 removals', self.run_play().stdout)
        self.s['extra_paths'][self.members_path] = []
        self.assertIn('0 additions, 0 removals', self.run_play().stdout)
        self.s['extra_paths'][admin_path] = []
        self.assertIn('0 additions, 1 removals', self.run_play().stdout)
        self.assertTrue(all(method == 'GET' for method, _ in self.s['calls']))
