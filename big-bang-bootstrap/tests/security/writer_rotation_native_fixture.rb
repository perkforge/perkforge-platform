# Synthetic model/service contracts only; does not load Rails or native configuration.
require 'ostruct'
require 'date'
module Gitlab
  VERSION = '19.4.2-ee'
  module Access; OWNER = 50; end
  def self.config; OpenStruct.new(gitlab: OpenStruct.new(host: 'gitlab.example.test', port: 443, https: true)); end
  module CurrentSettings; def self.admin_mode; false; end; end
end
class GroupMember
 attr_accessor :source_id,:user_id,:access_level,:expires_at
 def initialize;@source_id=7;@user_id=8;@access_level=50;@expires_at=nil;end
end
class Actor
 attr_accessor :id,:members,:admin,:active,:external,:bot
 def initialize(id,admin,bot);@id=id;@admin=admin;@active=true;@external=false;@bot=bot;@members=bot ? [GroupMember.new] : [];end
 def active?;@active;end
 def admin?;@admin;end
 def external?;@external;end
 def project_bot?;@bot;end
end
class User;def self.find_by(id:);$users[id];end;end
class Identity
 def self.where(**args);raise unless args=={provider:'openid_connect',extern_uid:'64f9a45d-083e-43b8-be26-e796dfd20928'};self;end
 def self.limit(n);raise unless n==2;self;end
 def self.pluck(k);$bindings;end
end
class Group
 def self.find_by(id:);id==7 ? new : nil;end
 def id;7;end
 def full_path;'tenants';end
 def parent_id;nil;end
 def private?;true;end
 def member(bot);bot.members.find{|m|m.source_id==7};end
end
class PersonalAccessToken
 attr_accessor :id,:user,:name,:description,:scopes,:expires_at,:previous_personal_access_token_id,:token,:revoked,:granular
 def initialize(id)
  @id=id;@user=$users[8];@name='identity-writer-'+('a'*12);@description='PerkForge identity bootstrap '+('a'*64);@scopes=['api'];@expires_at=Date.today-1;@token='synthetic.token.only';@revoked=false;@granular=false
 end
 def user_id;user.id;end
 def impersonation;false;end
 def sudo;false;end
 def granular?;@granular;end
 def granular_scopes;[];end
 def expired?;expires_at<Date.today;end
 def revoked?;@revoked;end
 def reload;self;end
 def with_lock;$locks+=1;yield;end
 def self.find_by(id:);$tokens[id];end
 def self.where(previous_personal_access_token_id:);OpenStruct.new(exists?:$tokens.values.any?{|t|t.previous_personal_access_token_id==previous_personal_access_token_id});end
end
Result=Struct.new(:payload) { def success?;true;end }
module GroupAccessTokens
 class RotateService
  def initialize(actor,old,parent,params);raise unless actor.id==3 && old.id==2 && parent.id==7 && params.keys==[:expires_at];@old=old;@expiry=params[:expires_at];end
  def execute
   $rotations+=1;@old.revoked=true;n=PersonalAccessToken.new(9);n.expires_at=@expiry;n.previous_personal_access_token_id=2;$tokens[9]=n
   n.token="invalid\nsecret" if $bad_token
   n.previous_personal_access_token_id=99 if $foreign_successor
   raise 'opaque after commit' if $lost
   Result.new({personal_access_token:n})
  end
 end
end
module ResourceAccessTokens
 class RevokeService
  def initialize(actor,parent,token);raise unless actor.id==3 && parent.id==7;@token=token;end
  def execute;$revokes<<@token.id;@token.revoked=true;Result.new({});end
 end
end
require '/source/gitlab-writer-rotation.rb'
def reset
 $users={3=>Actor.new(3,true,false),8=>Actor.new(8,false,true)};$tokens={2=>PersonalAccessToken.new(2)};$bindings=[3];$rotations=0;$locks=0;$revokes=[];$bad_token=false;$foreign_successor=false;$lost=false
end
def input
 {'run'=>true,'mode'=>'rotate','gitlab_origin'=>'https://gitlab.example.test','actor_native_id'=>3,'actor_subject'=>'64f9a45d-083e-43b8-be26-e796dfd20928','parent_id'=>7,'old_token_id'=>2,'expected_bot_id'=>8,'original_setup_id'=>'a'*64,'attempt_id'=>'b'*64,'expires_at'=>(Date.today+1).iso8601}
end
def execute(d=input);PerkforgeIdentityWriterRotation.execute(d);end
def assert(v);raise 'fixture assertion' unless v;end
reset;assert(execute({'run'=>false})=={'stage'=>'Inert'});assert($rotations==0)
[
 ->{input.merge('parent_id'=>99)}, ->{input.merge('old_token_id'=>99)}, ->{input.merge('actor_subject'=>'0'*36)},
 ->{input.merge('expires_at'=>(Date.today+4).iso8601)}, ->{input.merge('expires_at'=>Date.today.iso8601)},
 ->{input.merge('extra'=>'no')}, ->{$tokens[2].revoked=true;input}, ->{$tokens[2].expires_at=Date.today+1;input},
 ->{$tokens[2].scopes=['api','sudo'];input}, ->{$tokens[2].description='foreign';input},
 ->{$users[8].members<<GroupMember.new;input}, ->{$users[8].members[0].expires_at=Date.today+1;input},
 ->{$users[8].external=true;input}, ->{$bindings=[3,4];input}, ->{$users[8].admin=true;input},
 ->{$tokens[9]=PersonalAccessToken.new(9);$tokens[9].previous_personal_access_token_id=2;input}
].each do |mutation|
 reset;d=mutation.call;r=execute(d);assert(r['stage']=='ManualRecovery' && $rotations==0 && $revokes.empty? && !r.key?('successor_token'))
end
reset;r=execute;assert(r['stage']=='Rotated' && r['successor_id']==9 && r['bot_id']==8 && r['attempt_id']=='b'*64 && $locks==1 && $rotations==1 && $tokens[2].revoked?)
assert(execute['stage']=='ManualRecovery' && $rotations==1)
c=input.merge('mode'=>'revoke-successor','successor_id'=>9);r=execute(c);assert(r['stage']=='Revoked' && !r.key?('successor_token') && $revokes==[9]);assert(execute(c)['stage']=='Revoked' && $revokes==[9])
reset;$lost=true;r=execute;assert(r['stage']=='ManualRecovery' && r['successor_id'].nil? && $tokens[2].revoked? && !$tokens[9].revoked? && $revokes.empty?);assert(execute['stage']=='ManualRecovery' && $rotations==1)
reset;$foreign_successor=true;r=execute;assert(r['stage']=='ManualRecovery' && $revokes.empty?)
reset;$bad_token=true;r=execute;assert(r['stage']=='ManualRecovery' && r['successor_revoked']==true && $revokes==[9])
reset;$tokens[2].revoked=true;$tokens[9]=PersonalAccessToken.new(9);$tokens[9].previous_personal_access_token_id=99;r=execute(input.merge('mode'=>'revoke-successor','successor_id'=>9));assert(r['stage']=='ManualRecovery' && $revokes.empty?)
puts 'PASS synthetic rotation guards, one-successor cleanup and uncertain-response preservation'
