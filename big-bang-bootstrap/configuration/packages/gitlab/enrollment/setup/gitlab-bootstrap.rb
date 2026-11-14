# frozen_string_literal: true
# Included only by the fixed host coordinator. No standalone token-printing mode.
require 'json'
require 'date'
require 'uri'
module PerkforgeIdentityBootstrap
  def self.execute(input)
    return { 'stage' => 'Inert' } unless input['run'] == true
    raise 'version' unless ['19.4.2', '19.4.2-ee'].include?(Gitlab::VERSION)
    raise 'admin mode unsupported' if Gitlab::CurrentSettings.admin_mode
    uri = URI.parse(input.fetch('gitlab_origin'))
    raise 'origin' unless uri.scheme == 'https' && Gitlab.config.gitlab.host == uri.host && Gitlab.config.gitlab.https
    actor = User.find_by(id: input.fetch('actor_native_id'))
    raise 'actor' unless actor&.active? && actor.admin?
    bindings = Identity.where(provider: 'openid_connect', extern_uid: input.fetch('actor_subject')).limit(2).pluck(:user_id)
    raise 'actor binding' unless bindings == [actor.id]
    setup = input.fetch('setup_id')
    description = "PerkForge identity bootstrap #{setup}"
    parent = nil
    writer = nil
    reader = nil
    owned_writer = false
    owned_reader = false
    stage = 'NativePreflight'
    if input.fetch('mode') == 'revoke'
      parent = Group.find_by(id: input.fetch('parent_id'))
      raise 'parent' unless parent && parent.full_path == 'tenants' && parent.parent_id.nil? && parent.private?
      writer = PersonalAccessToken.find_by(id: input.fetch('writer_token_id'))
      reader = PersonalAccessToken.find_by(id: input.fetch('reader_token_id'))
      raise 'token ownership' unless writer && reader && writer.description == description && reader.description == description && reader.user_id == actor.id && writer.user.project_bot? && parent.member(writer.user)&.access_level == Gitlab::Access::OWNER
      owned_writer = true
      owned_reader = true
      wr = ResourceAccessTokens::RevokeService.new(actor, parent, writer).execute
      rr = PersonalAccessTokens::RevokeService.new(actor, token: reader, source: :self).execute
      return { 'stage' => (wr.success? && rr.success? ? 'Revoked' : 'ManualRecovery'), 'parent_id' => parent.id, 'writer_token_id' => writer.id, 'reader_token_id' => reader.id }
    end
    raise 'mode' unless input['mode'] == 'mint' && input['allow_parent_create'] == true
    expiry = Date.iso8601(input.fetch('expires_at'))
    remaining = Time.utc(expiry.year, expiry.month, expiry.day) - Time.now.utc
    raise 'expiry' unless remaining >= 3600 && remaining <= 172800
    raise 'token issuance denied' unless Ability.allowed?(actor, :create_personal_access_token, actor)
    raise 'granular-only issuance unsupported' if Feature.enabled?(:granular_personal_access_tokens, actor) && Gitlab::CurrentSettings.granular_tokens_enforced?
    raise 'foreign parent' if Namespace.where(parent_id: nil, path: 'tenants').exists?
    raise 'default integrations' if Integration.where(instance: true, active: true).exists?
    stage = 'ParentCreation'
    result = Groups::CreateService.new(actor, { name: 'Tenants', path: 'tenants', visibility_level: Gitlab::VisibilityLevel::PRIVATE, organization_id: actor.organization_id }).execute
    raise 'parent creation' unless result.success?
    parent = result.payload.fetch(:group)
    raise 'parent readback' unless parent.full_path == 'tenants' && parent.parent_id.nil? && parent.private? && parent.member(actor)&.access_level == Gitlab::Access::OWNER
    stage = 'WriterCreation'
    result = ResourceAccessTokens::CreateService.new(actor, parent, { name: "identity-writer-#{setup[0, 12]}", scopes: ['api'], access_level: Gitlab::Access::OWNER, expires_at: expiry, description: description }).execute
    raise 'writer creation' unless result.success?
    writer = result.payload.fetch(:access_token)
    owned_writer = true
    raise 'writer readback' unless writer.scopes == ['api'] && !writer.user.admin? && writer.user.project_bot? && parent.member(writer.user)&.access_level == Gitlab::Access::OWNER
    stage = 'ReaderCreation'
    result = PersonalAccessTokens::CreateService.new(current_user: actor, target_user: actor, organization_id: actor.organization_id, params: { name: "identity-reader-#{setup[0, 12]}", scopes: ['read_api'], expires_at: expiry, description: description, impersonation: false, sudo: false }).execute
    raise 'reader creation' unless result.success?
    reader = result.payload.fetch(:personal_access_token)
    owned_reader = true
    raise 'reader readback' unless reader.user_id == actor.id && reader.scopes == ['read_api']
    { 'stage' => 'Minted', 'parent_id' => parent.id, 'writer_token_id' => writer.id, 'reader_token_id' => reader.id, 'writer_token' => writer.token, 'reader_token' => reader.token }
  rescue StandardError
    # Preserve parent/bot ownership. Never delete shared resources or other tokens.
    writer_revoked = owned_writer ? false : nil
    reader_revoked = owned_reader ? false : nil
    begin
      writer_revoked = ResourceAccessTokens::RevokeService.new(actor, parent, writer).execute.success? if owned_writer && writer && parent
    rescue StandardError
      writer_revoked = false
    end
    begin
      reader_revoked = PersonalAccessTokens::RevokeService.new(actor, token: reader, source: :self).execute.success? if owned_reader && reader
    rescue StandardError
      reader_revoked = false
    end
    { 'stage' => 'ManualRecovery', 'substage' => stage || 'NativePreflight', 'parent_id' => parent&.id, 'writer_token_id' => (owned_writer ? writer&.id : nil), 'reader_token_id' => (owned_reader ? reader&.id : nil), 'writer_revoked' => writer_revoked, 'reader_revoked' => reader_revoked }
  end
end
