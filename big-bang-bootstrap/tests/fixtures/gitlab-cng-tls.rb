# Verification only: isolated loopback TLS protocol fixture, no real DB or Rails app.
require 'json'
require 'socket'
require 'openssl'
require 'active_record'
require 'active_record/connection_adapters/postgresql_adapter'
require 'pg'
root = ARGV.fetch(0)
version = File.read('/srv/gitlab/VERSION').strip
abort 'Unexpected GitLab runtime version' unless version.start_with?('19.4.2')
def connect_fixture(root, host: 'postgres.fixture.invalid', ca: 'ca.crt', plaintext: false, explicit: nil)
  server = TCPServer.new('127.0.0.1', 0)
  port = server.addr[1]
  context = OpenSSL::SSL::SSLContext.new
  context.cert = OpenSSL::X509::Certificate.new(File.read(File.join(root, 'server.crt')))
  context.key = OpenSSL::PKey.read(File.read(File.join(root, 'server.key')))
  thread = Thread.new do
    begin
      loop do
        raw = server.accept
        begin
          raise 'Unexpected PostgreSQL SSL request' unless raw.read(8) == [8,80877103].pack('NN')
          raw.write(plaintext ? 'N' : 'S')
          unless plaintext
            peer = OpenSSL::SSL::SSLSocket.new(raw, context)
            peer.sync_close = true
            peer.accept
            peer.readpartial(8192)
            body = "SFATAL\0C28000\0Moffline CNG TLS reached\0\0"
            peer.write('E' + [body.bytesize+4].pack('N') + body)
            peer.close
          end
        rescue OpenSSL::SSL::SSLError, EOFError, IOError, Errno::ECONNRESET, Errno::EPIPE
          # A rejected TLS identity can be followed by ActiveRecord's retry.
        ensure
          raw.close unless raw.closed?
        end
      end
    rescue IOError, Errno::EBADF
      # The caller closes the listening socket after all adapter retries finish.
    end
  end
  old_mode,old_ca = ENV['PGSSLMODE'],ENV['PGSSLROOTCERT']
  begin
    ENV['PGSSLMODE'] = 'verify-full'
    ENV['PGSSLROOTCERT'] = File.join(root,ca)
    settings = {adapter: 'postgresql',host: host,hostaddr: '127.0.0.1',port: port,database: 'cng_transport_probe',username: 'cng_transport_user',password: 'offline_fixture_only',connect_timeout: 3,gssencmode: 'disable'}
    settings[:sslmode] = explicit if explicit
    begin
      ActiveRecord::Base.establish_connection(settings)
      ActiveRecord::Base.connection.raw_connection
      raise 'Unexpected database authentication; fixture must stop after TLS'
    rescue ActiveRecord::ActiveRecordError, PG::Error => e
      messages = []
      while e && !messages.include?(e.message)
        messages << e.message
        e = e.cause
      end
      messages.join("\n")
    end
  ensure
    ActiveRecord::Base.remove_connection
    old_mode.nil? ? ENV.delete('PGSSLMODE') : ENV['PGSSLMODE'] = old_mode
    old_ca.nil? ? ENV.delete('PGSSLROOTCERT') : ENV['PGSSLROOTCERT'] = old_ca
    server.close unless server.closed?
    unless thread.join(6)
      thread.kill
      thread.join
      raise 'Loopback server did not terminate'
    end
    thread.value
  end
end
results = {}
matching = connect_fixture(root)
results[:matching_ca_and_hostname] = matching.include?('offline CNG TLS reached')
wrong = connect_fixture(root,host: 'wrong.fixture.invalid')
results[:wrong_hostname_rejected] = wrong.include?('does not match host name') && !wrong.include?('offline CNG TLS reached')
wrong_ca = connect_fixture(root,ca: 'other.crt')
results[:wrong_ca_rejected] = wrong_ca.include?('certificate verify failed') && !wrong_ca.include?('offline CNG TLS reached')
missing = connect_fixture(root,ca: 'missing.crt')
results[:missing_ca_rejected] = missing.include?('does not exist') && !missing.include?('offline CNG TLS reached')
plain = connect_fixture(root,plaintext: true)
results[:plaintext_rejected] = plain.include?('does not support SSL')
control = connect_fixture(root,host: 'wrong.fixture.invalid',explicit: 'verify-ca')
results[:explicit_ca_only_control_accepts_wrong_hostname] = control.include?('offline CNG TLS reached')
diagnostics = results.values.all? ? {} : {matching: matching.to_s[0,1200],wrong_hostname: wrong.to_s[0,1200],wrong_ca: wrong_ca.to_s[0,1200],missing_ca: missing.to_s[0,1200],plaintext: plain.to_s[0,1200],control: control.to_s[0,1200]}
puts JSON.generate({diagnostics: diagnostics,gitlab_version: version,ruby: RUBY_VERSION,active_record: ActiveRecord::VERSION::STRING,pg: PG::VERSION,libpq: PG.library_version,results: results})
exit(results.values.all? ? 0 : 1)
