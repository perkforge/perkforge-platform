# frozen_string_literal: true
# Fixed coordinator include only. No CLI, stdout, credential lookup or family API.
require 'date'
require 'uri'
module PerkforgeIdentityWriterRotation
  SUBJECT = '64f9a45d-083e-43b8-be26-e796dfd20928'
  def self.execute(input)
    return { 'stage' => 'Inert' } unless input.is_a?(Hash) && input['run'] == true
    base = %w[run mode gitlab_origin actor_native_id actor_subject parent_id old_token_id expected_bot_id original_setup_id attempt_id expires_at]
    expected = base + (input['mode'] == 'revoke-successor' ? ['successor_id'] : [])
    raise 'input' unless input.keys.sort == expected.sort && %w[rotate revoke-successor].include?(input['mode'])
    raise 'fixed integer IDs' unless %w[actor_native_id parent_id old_token_id].all? { |k| input[k].is_a?(Integer) }
    raise 'binding' unless input['actor_native_id'] == 3 && input['actor_subject'] == SUBJECT && input['parent_id'] == 7 && input['old_token_id'] == 2
    raise 'bot id' unless input['expected_bot_id'].is_a?(Integer) && input['expected_bot_id'] > 0
    %w[original_setup_id attempt_id].each { |k| raise 'id' unless input[k].is_a?(String) && input[k].match?(/\A[a-f0-9]{64}\z/) }
    raise 'version' unless ['19.4.2', '19.4.2-ee'].include?(Gitlab::VERSION)
    raise 'admin mode unsupported' if Gitlab::CurrentSettings.admin_mode
    raise 'origin' unless input['gitlab_origin'].is_a?(String) && input['gitlab_origin'].match?(%r{\Ahttps://[A-Za-z0-9.-]+(?::[0-9]+)?\z})
    uri = URI.parse(input['gitlab_origin'])
    raise 'origin' unless uri.host == Gitlab.config.gitlab.host && uri.port == Gitlab.config.gitlab.port && Gitlab.config.gitlab.https
    expiry = Date.iso8601(input.fetch('expires_at'))
    raise 'date' unless expiry.iso8601 == input['expires_at']
    actor = User.find_by(id: 3)
    raise 'actor' unless actor&.active? && actor.admin?
    raise 'subject' unless Identity.where(provider: 'openid_connect', extern_uid: SUBJECT).limit(2).pluck(:user_id) == [3]
    parent = Group.find_by(id: 7)
    raise 'parent' unless parent && parent.full_path == 'tenants' && parent.parent_id.nil? && parent.private?
    old = PersonalAccessToken.find_by(id: 2)
    bot = old&.user
    raise 'bot' unless bot && bot.id == input['expected_bot_id'] && bot.active? && !bot.admin? && bot.project_bot? && bot.external? == actor.external?
    members = bot.members.to_a
    raise 'sole membership' unless members.length == 1 && members[0].is_a?(GroupMember) && members[0].source_id == 7 && members[0].user_id == bot.id && members[0].access_level == Gitlab::Access::OWNER && members[0].expires_at.nil?
    raise 'direct owner' unless parent.member(bot)&.access_level == Gitlab::Access::OWNER
    raise 'old ownership' unless owned?(old, input, bot)
    binding = { 'parent_id' => 7, 'old_token_id' => 2, 'bot_id' => bot.id, 'expires_at' => expiry.iso8601, 'attempt_id' => input['attempt_id'], 'original_setup_id' => input['original_setup_id'] }
    stage = 'NativePreflight'
    if input['mode'] == 'revoke-successor'
      id = input['successor_id']
      raise 'successor id' unless id.is_a?(Integer) && id > 0 && id != 2
      successor = PersonalAccessToken.find_by(id: id)
      raise 'successor ownership' unless old.revoked? && owned?(successor, input, bot) && successor.previous_personal_access_token_id == 2 && successor.expires_at == expiry
      # Cleanup only the exact successor from the protected coordinator receipt.
      result = ResourceAccessTokens::RevokeService.new(actor, parent, successor).execute unless successor.revoked?
      raise 'revoke' unless successor.reload.revoked? && (result.nil? || result.success?)
      return binding.merge('stage' => 'Revoked', 'successor_id' => id)
    end
    remaining = Time.utc(expiry.year, expiry.month, expiry.day) - Time.now.utc
    raise 'expiry' unless remaining >= 3600 && remaining <= 172800
    # Native row lock prevents a second local/native rotation racing this check.
    # Do not use a revoked old-token rotation endpoint: it may revoke the family.
    stage = 'Rotation'
    result = old.with_lock do
      raise 'old changed' unless owned?(old, input, bot) && old.expired? && !old.revoked?
      raise 'existing successor' if PersonalAccessToken.where(previous_personal_access_token_id: 2).exists?
      GroupAccessTokens::RotateService.new(actor, old, parent, { expires_at: expiry }).execute
    end
    raise 'rotation result' unless result.success?
    successor = result.payload.fetch(:personal_access_token)
    stage = 'SuccessorReadback'
    raise 'successor ownership' unless successor.id.is_a?(Integer) && successor.id > 0 && successor.id != 2 && owned?(successor, input, bot) && successor.previous_personal_access_token_id == 2 && successor.expires_at == expiry && old.reload.revoked? && !successor.revoked?
    verified_successor = true
    raise 'token' unless successor.token.is_a?(String) && successor.token.match?(/\A[A-Za-z0-9_.-]{8,4096}\z/)
    binding.merge('stage' => 'Rotated', 'successor_id' => successor.id, 'successor_token' => successor.token)
  rescue StandardError
    revoked = nil
    # A mismatched/unknown successor is never revoked based only on returned ID.
    if verified_successor && successor && actor && parent
      begin
        response = ResourceAccessTokens::RevokeService.new(actor, parent, successor).execute
        revoked = response.success? && successor.reload.revoked?
      rescue StandardError
        revoked = false
      end
    end
    (binding || {}).merge('stage' => 'ManualRecovery', 'substage' => stage || 'NativePreflight', 'successor_id' => (verified_successor ? successor.id : nil), 'successor_revoked' => revoked)
  end

  def self.owned?(token, input, bot)
    token && token.user_id == bot.id && token.name == "identity-writer-#{input['original_setup_id'][0, 12]}" &&
      token.description == "PerkForge identity bootstrap #{input['original_setup_id']}" && token.scopes == ['api'] &&
      !token.impersonation && !token.sudo && !token.granular? && token.granular_scopes.empty?
  end
  private_class_method :owned?
end
