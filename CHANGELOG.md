# Changelog

## [0.44.0](https://github.com/perkforge/perkforge-platform/compare/v0.43.0...v0.44.0) (2026-11-14)


### Features

* **mattermost:** prepare dedicated native PostgreSQL and file PVC backends ([#387](https://github.com/perkforge/perkforge-platform/pull/387)).
* **mattermost:** stage scoped runtime custody, native activation and append-only chat DNS maintenance ([#396](https://github.com/perkforge/perkforge-platform/pull/396)).

* **alerting:** provision scoped Portal Grafana ntfy routing ([#381](https://github.com/perkforge/perkforge-platform/issues/381)) ([5a862ac](https://github.com/perkforge/perkforge-platform/commit/5a862acb8450cce55ca0061d9de09ee7ce9d809e))
* deliver platform-alerts with additive scoped credentials ([#386](https://github.com/perkforge/perkforge-platform/issues/386)) ([a88dea7](https://github.com/perkforge/perkforge-platform/commit/a88dea7658fa09419d6d7bdf8124ab1653128ae2))
* **notifications:** add native Flux deployment outcome route ([#389](https://github.com/perkforge/perkforge-platform/issues/389)) ([bd8a5e7](https://github.com/perkforge/perkforge-platform/commit/bd8a5e76d629331fe91391a91d9a5c0414951a97))
* **notifications:** deliver scoped native platform deployment route ([#392](https://github.com/perkforge/perkforge-platform/issues/392)) ([fbbe1f2](https://github.com/perkforge/perkforge-platform/commit/fbbe1f2534af89c6486feeb0cc1b04f0e91c21d9))
* **observability:** add portable platform resource alert catalog ([#384](https://github.com/perkforge/perkforge-platform/issues/384)) ([bc2d309](https://github.com/perkforge/perkforge-platform/commit/bc2d30921185c1f7b3f8fdfc32ac57f5267dcb2f))
* **portal:** select reviewed integrated enrollment without changing existing apps ([#378](https://github.com/perkforge/perkforge-platform/issues/378)) ([14beda8](https://github.com/perkforge/perkforge-platform/commit/14beda8a89960cd2314d54065f8c08f1eefbeda4))
* select released Portal identity explorer enrollment ([#394](https://github.com/perkforge/perkforge-platform/issues/394)) ([b90ca75](https://github.com/perkforge/perkforge-platform/commit/b90ca7510be1effd5fac37228ab1216232b0be88))


### Bug Fixes

* **alerting:** guard effective Helm secret mounts ([#382](https://github.com/perkforge/perkforge-platform/issues/382)) ([22db374](https://github.com/perkforge/perkforge-platform/commit/22db37445602abdf38b57c463538f3249aba3497))
* **alerts:** avoid pointer-formatted truncated count ([#390](https://github.com/perkforge/perkforge-platform/issues/390)) ([177fe49](https://github.com/perkforge/perkforge-platform/commit/177fe499e5f9a527ed4fe263dc82899f3f3e2cd0))
* **mattermost:** restrict pinned operator runtime writes ([#385](https://github.com/perkforge/perkforge-platform/issues/385)) ([5a3b193](https://github.com/perkforge/perkforge-platform/commit/5a3b193d76126f3347de7a3bfdc589b5f2237a3c))
* **ntfy:** preserve one phone token across exact reader topics ([#388](https://github.com/perkforge/perkforge-platform/issues/388)) ([41d8c4e](https://github.com/perkforge/perkforge-platform/commit/41d8c4eec2b8f4a02e01790eb878813cf38f77cd))
* **portal:** promote verified admin-only enrollment release ([#380](https://github.com/perkforge/perkforge-platform/issues/380)) ([e7152ac](https://github.com/perkforge/perkforge-platform/commit/e7152accff0829b77ac13471cf460293b35b6c9a))

## [0.43.0](https://github.com/perkforge/perkforge-platform/compare/v0.42.0...v0.43.0) (2026-11-14)


### Features

* **eso:** compose native activation with existing ntfy root ([#367](https://github.com/perkforge/perkforge-platform/issues/367)) ([8326cb9](https://github.com/perkforge/perkforge-platform/commit/8326cb98c41128bfc7c5fe9cb85854470c3eabf2))
* **ntfy:** add verified exact-topic owner subscriber workflow ([#375](https://github.com/perkforge/perkforge-platform/issues/375)) ([fe15b24](https://github.com/perkforge/perkforge-platform/commit/fe15b24b73dce7fa2b14f7e058755e1238f7544a))
* **ntfy:** prepare exact-topic native auth with lifecycle guards ([#363](https://github.com/perkforge/perkforge-platform/issues/363)) ([0c5bc9d](https://github.com/perkforge/perkforge-platform/commit/0c5bc9d01558b78d955fa388aad7e81acf8e5a19))
* **ntfy:** prepare scoped publisher-only protected runtime delivery ([#373](https://github.com/perkforge/perkforge-platform/issues/373)) ([559948e](https://github.com/perkforge/perkforge-platform/commit/559948ed846aadfdca0b86e2fe2928ff28bacdf4))
* **observability:** deploy portable query runtime delivery ([#368](https://github.com/perkforge/perkforge-platform/issues/368)) ([1fbe594](https://github.com/perkforge/perkforge-platform/commit/1fbe5949d4a793333693154e829204047856e975))
* **observability:** stage inactive loopback backend chart candidate ([#361](https://github.com/perkforge/perkforge-platform/issues/361)) ([3d390e3](https://github.com/perkforge/perkforge-platform/commit/3d390e3874d628c07e94a633d589dd6c00e3b6ef))


### Bug Fixes

* **dns:** support explicit fix-forward maintenance failures ([#376](https://github.com/perkforge/perkforge-platform/issues/376)) ([a2ed11c](https://github.com/perkforge/perkforge-platform/commit/a2ed11cad3a572eaeb2f46e806b5170ac75b3d74))
* **eso:** permit exact API Service discovery during native rendering ([#369](https://github.com/perkforge/perkforge-platform/issues/369)) ([7adaba3](https://github.com/perkforge/perkforge-platform/commit/7adaba3fcf9dbabfd98151c73569bbbb9a1c5602))
* **ntfy:** allow ESO self-token validation ([#374](https://github.com/perkforge/perkforge-platform/issues/374)) ([1f8a98c](https://github.com/perkforge/perkforge-platform/commit/1f8a98c77dffe63cc85ae4581f350e5f26800615))
* **observability:** allow no-surge Grafana rollout by target ([#370](https://github.com/perkforge/perkforge-platform/issues/370)) ([7c031e4](https://github.com/perkforge/perkforge-platform/commit/7c031e458638705deb1671a33b882602b8bb1e05))
* **observability:** permit Flux query health observation ([#372](https://github.com/perkforge/perkforge-platform/issues/372)) ([e5685a5](https://github.com/perkforge/perkforge-platform/commit/e5685a5967a0cea4506fe14ce7af1b1874734768))
* **observability:** scope Flux query runtime authority ([#371](https://github.com/perkforge/perkforge-platform/issues/371)) ([bd49cad](https://github.com/perkforge/perkforge-platform/commit/bd49cad804d64a1fb79b5b12a09819bcffe04691))

## [0.42.0](https://github.com/perkforge/perkforge-platform/compare/v0.41.0...v0.42.0) (2026-11-13)


### Features

* **observability:** authenticate platform variable read APIs ([#360](https://github.com/perkforge/perkforge-platform/issues/360)) ([41ecb44](https://github.com/perkforge/perkforge-platform/commit/41ecb44b7db650e33b14e35a1ba76163a3b3537a))


### Bug Fixes

* **ntfy:** decouple DNS prerequisite from Portal rollout ([#359](https://github.com/perkforge/perkforge-platform/issues/359)) ([73cf204](https://github.com/perkforge/perkforge-platform/commit/73cf204d8c6ccba7d3224de30d9c3aed1e5ad61c))
* **ntfy:** permit read-only Flux pod health checks ([#356](https://github.com/perkforge/perkforge-platform/issues/356)) ([c9502e8](https://github.com/perkforge/perkforge-platform/commit/c9502e8a6d6638c788a2207095274bc6999149d9))

## [0.41.0](https://github.com/perkforge/perkforge-platform/compare/v0.40.0...v0.41.0) (2026-11-13)


### Features

* **observability:** package inactive tenant query gateway ([#355](https://github.com/perkforge/perkforge-platform/issues/355)) ([d581cc9](https://github.com/perkforge/perkforge-platform/commit/d581cc997eb5de0e16a4219ff5dc1ba4019e6b9b))


### Bug Fixes

* **ntfy:** add fixed DNS maintenance scope ([#354](https://github.com/perkforge/perkforge-platform/issues/354)) ([399f9ee](https://github.com/perkforge/perkforge-platform/commit/399f9ee0570faba8c61fd6523dbfa26dfddcb7a1))
* **ntfy:** place persistent workload on storage workers ([#352](https://github.com/perkforge/perkforge-platform/issues/352)) ([586752b](https://github.com/perkforge/perkforge-platform/commit/586752b6cecdc1518a470ab1ab7a02233aaddbb9))

## [0.40.0](https://github.com/perkforge/perkforge-platform/compare/v0.39.0...v0.40.0) (2026-11-13)


### Features

* **alerting:** prepare context-scoped dual delivery ([#337](https://github.com/perkforge/perkforge-platform/issues/337)) ([13b2d5a](https://github.com/perkforge/perkforge-platform/commit/13b2d5ab2c6b2e52d4a9a2bffd43cad44c725545))
* **gitlab:** add native metrics alert candidate ([#347](https://github.com/perkforge/perkforge-platform/issues/347)) ([fd0167e](https://github.com/perkforge/perkforge-platform/commit/fd0167e660a3cf338e958792e64359535568e120))
* **gitlab:** define scoped event ingress contract ([#343](https://github.com/perkforge/perkforge-platform/issues/343)) ([241ca6a](https://github.com/perkforge/perkforge-platform/commit/241ca6a1653ab7fd26ea3613fdaf0a93738e3150))
* **gitlab:** verify exact tenant project context read-only ([#336](https://github.com/perkforge/perkforge-platform/issues/336)) ([02a148b](https://github.com/perkforge/perkforge-platform/commit/02a148bfd96658c773ba4cca11c0ee74fa9adb1f))
* **identity:** define inactive Portal context contract ([#340](https://github.com/perkforge/perkforge-platform/issues/340)) ([fe247b3](https://github.com/perkforge/perkforge-platform/commit/fe247b343db0b42fa0368adf03af3b027218f9ae))
* **identity:** gate Portal generic group role mappings ([#342](https://github.com/perkforge/perkforge-platform/issues/342)) ([e83e2aa](https://github.com/perkforge/perkforge-platform/commit/e83e2aa2dfa0993fd23f9c355b61364c7878a7fc))
* **mattermost:** gate authoritative channel membership reconciliation ([#346](https://github.com/perkforge/perkforge-platform/issues/346)) ([b7581e7](https://github.com/perkforge/perkforge-platform/commit/b7581e7be93b5c257bd7378c42253a2076e0a062))
* **mattermost:** verify native tenant alert context ([#338](https://github.com/perkforge/perkforge-platform/issues/338)) ([93d7a0b](https://github.com/perkforge/perkforge-platform/commit/93d7a0b943f52dd0b9aa3f1add0c4e7eb2175861))
* **ntfy:** add unselected native deployment candidate ([#345](https://github.com/perkforge/perkforge-platform/issues/345)) ([cac1237](https://github.com/perkforge/perkforge-platform/commit/cac1237c57dd02194efd661b5a3478fbe42ded93))
* **ntfy:** prepare verified backend routing candidate ([#348](https://github.com/perkforge/perkforge-platform/issues/348)) ([adbbc0d](https://github.com/perkforge/perkforge-platform/commit/adbbc0d963bacb249231b5019798848e8e0a9d29))
* **ntfy:** stage approved local GitOps activation ([#351](https://github.com/perkforge/perkforge-platform/issues/351)) ([3be72e9](https://github.com/perkforge/perkforge-platform/commit/3be72e9dfdb5fb87a87ef5b65119bce985f9cc27))
* **observability:** add inactive authenticated tenant query gateway ([#344](https://github.com/perkforge/perkforge-platform/issues/344)) ([2dd8ba3](https://github.com/perkforge/perkforge-platform/commit/2dd8ba3f44abb3257ea79b91e47a53ece6dccfd8))
* **observability:** verify authenticated tenant data plane natively ([#350](https://github.com/perkforge/perkforge-platform/issues/350)) ([23c8c38](https://github.com/perkforge/perkforge-platform/commit/23c8c389a377320d48563e9ea3ee998ddaa01caf))

## [0.39.0](https://github.com/perkforge/perkforge-platform/compare/v0.38.0...v0.39.0) (2026-11-12)


### Features

* stage physical backup target without starting NFS ([#329](https://github.com/perkforge/perkforge-platform/issues/329)) ([e903ee0](https://github.com/perkforge/perkforge-platform/commit/e903ee08c40ff867fcce1aa3bfbb7f764130c4f6))


### Bug Fixes

* support reviewed backup-host pod subnet ([#330](https://github.com/perkforge/perkforge-platform/issues/330)) ([62d022a](https://github.com/perkforge/perkforge-platform/commit/62d022a53a1f437d9d4aa9e915e0b6e2234650ee))

## [0.38.0](https://github.com/perkforge/perkforge-platform/compare/v0.37.2...v0.38.0) (2026-11-11)


### Features

* **eso:** add guarded native activation inputs ([#326](https://github.com/perkforge/perkforge-platform/issues/326)) ([76b6a97](https://github.com/perkforge/perkforge-platform/commit/76b6a97c2d33cef5e47ebdb67468ff359c121608))

## [0.37.2](https://github.com/perkforge/perkforge-platform/compare/v0.37.1...v0.37.2) (2026-11-11)


### Bug Fixes

* **eso:** avoid copying Ansible lazy template context ([#324](https://github.com/perkforge/perkforge-platform/issues/324)) ([2653cf5](https://github.com/perkforge/perkforge-platform/commit/2653cf5954ade10ae070c8b00e2bff425ee7c6ca))

## [0.37.1](https://github.com/perkforge/perkforge-platform/compare/v0.37.0...v0.37.1) (2026-11-11)


### Bug Fixes

* **eso:** verify managed ownership and Rancher namespace defaults ([#322](https://github.com/perkforge/perkforge-platform/issues/322)) ([1b753b6](https://github.com/perkforge/perkforge-platform/commit/1b753b6ba0240900adfadc1b5460ded9b9549f20))

## [0.37.0](https://github.com/perkforge/perkforge-platform/compare/v0.36.0...v0.37.0) (2026-11-10)


### Features

* **portal:** wire paused physical enrollment release ([#320](https://github.com/perkforge/perkforge-platform/issues/320)) ([704aedc](https://github.com/perkforge/perkforge-platform/commit/704aedc7c18e1f11f39ef82dc1bfe61a41614e96))

## [0.36.0](https://github.com/perkforge/perkforge-platform/compare/v0.35.0...v0.36.0) (2026-11-10)


### Features

* **platform:** prepare guarded physical Portal DNS scope ([#315](https://github.com/perkforge/perkforge-platform/issues/315)) ([90d9e4a](https://github.com/perkforge/perkforge-platform/commit/90d9e4a254e5708b2e164468cf923c2a4ffb7deb))

## [0.35.0](https://github.com/perkforge/perkforge-platform/compare/v0.34.3...v0.35.0) (2026-11-10)


### Features

* **secrets:** prepare native ESO and scoped OpenBao stores ([#316](https://github.com/perkforge/perkforge-platform/issues/316)) ([fbb01d0](https://github.com/perkforge/perkforge-platform/commit/fbb01d0835ff3893d27af4e5c19a2ce4b2a43c96))

## [0.34.3](https://github.com/perkforge/perkforge-platform/compare/v0.34.2...v0.34.3) (2026-11-10)


### Bug Fixes

* **nextcloud:** pin enrollment v1.5.4 [skip ci] ([#313](https://github.com/perkforge/perkforge-platform/issues/313)) ([e44eae9](https://github.com/perkforge/perkforge-platform/commit/e44eae9f46ef35c0957f3f2865823d67b2ce08ae))

## [0.34.2](https://github.com/perkforge/perkforge-platform/compare/v0.34.1...v0.34.2) (2026-11-10)


### Bug Fixes

* **nextcloud:** pin enrollment v1.5.3 [skip ci] ([#311](https://github.com/perkforge/perkforge-platform/issues/311)) ([456364c](https://github.com/perkforge/perkforge-platform/commit/456364c3fcac1d3cb79a676b2697abb45fc0a250))

## [0.34.1](https://github.com/perkforge/perkforge-platform/compare/v0.34.0...v0.34.1) (2026-11-09)


### Bug Fixes

* **nextcloud:** pin enrollment v1.5.2 for storage expansion [skip ci] ([#308](https://github.com/perkforge/perkforge-platform/issues/308)) ([443bc20](https://github.com/perkforge/perkforge-platform/commit/443bc20f720fd15d369b4724fb03ee191eda66aa))

## [0.34.0](https://github.com/perkforge/perkforge-platform/compare/v0.33.6...v0.34.0) (2026-11-09)


### Features

* bootstrap recovery secrets from Bitwarden into OpenBao ([#305](https://github.com/perkforge/perkforge-platform/issues/305)) ([74cb09a](https://github.com/perkforge/perkforge-platform/commit/74cb09a4a3c490604c26ceed067170f2d1aac8d7))

## [0.33.6](https://github.com/perkforge/perkforge-platform/compare/v0.33.5...v0.33.6) (2026-11-08)


### Bug Fixes

* **velero:** permit scoped maintenance cache reads ([#303](https://github.com/perkforge/perkforge-platform/issues/303)) ([d21b207](https://github.com/perkforge/perkforge-platform/commit/d21b20748e9e7f8b668f900fa78332589b53f6d2))

## [0.33.5](https://github.com/perkforge/perkforge-platform/compare/v0.33.4...v0.33.5) (2026-11-08)


### Bug Fixes

* **velero:** retain related PV backup metadata ([#301](https://github.com/perkforge/perkforge-platform/issues/301)) ([2073ce8](https://github.com/perkforge/perkforge-platform/commit/2073ce8152d4e2925ab551c3a5443397044d5384))

## [0.33.4](https://github.com/perkforge/perkforge-platform/compare/v0.33.3...v0.33.4) (2026-11-08)


### Bug Fixes

* **velero:** use writable repository home ([#299](https://github.com/perkforge/perkforge-platform/issues/299)) ([ba2a9bf](https://github.com/perkforge/perkforge-platform/commit/ba2a9bf1c59e409f1ffd647b1f3387a15776e392))

## [0.33.3](https://github.com/perkforge/perkforge-platform/compare/v0.33.2...v0.33.3) (2026-11-08)


### Bug Fixes

* **velero:** allow pinned PVC cache discovery ([#297](https://github.com/perkforge/perkforge-platform/issues/297)) ([8ced351](https://github.com/perkforge/perkforge-platform/commit/8ced351935b44267e43cdd468c58d8ecfd8adf58))

## [0.33.2](https://github.com/perkforge/perkforge-platform/compare/v0.33.1...v0.33.2) (2026-11-08)


### Bug Fixes

* **velero:** scope native action readiness reads ([#295](https://github.com/perkforge/perkforge-platform/issues/295)) ([080ccad](https://github.com/perkforge/perkforge-platform/commit/080ccade61263efc33729e3eb3f56f568e506870))

## [0.33.1](https://github.com/perkforge/perkforge-platform/compare/v0.33.0...v0.33.1) (2026-11-08)


### Bug Fixes

* **velero:** qualify backup APIs and scope binding discovery ([#293](https://github.com/perkforge/perkforge-platform/issues/293)) ([2d261b1](https://github.com/perkforge/perkforge-platform/commit/2d261b1ce3e43d18849994c8b8a4aa14fcfbdfd6))

## [0.33.0](https://github.com/perkforge/perkforge-platform/compare/v0.32.4...v0.33.0) (2026-11-08)


### Features

* **mattermost:** inherit Big Bang versions and prepare Keycloak SSO ([#116](https://github.com/perkforge/perkforge-platform/issues/116)) ([041e1e7](https://github.com/perkforge/perkforge-platform/commit/041e1e7c43a3112bb2f75f491a83681c71a1d65a))


### Bug Fixes

* **velero:** size Garage CPU request for local PoC ([#289](https://github.com/perkforge/perkforge-platform/issues/289)) ([7ae34fd](https://github.com/perkforge/perkforge-platform/commit/7ae34fdc9a4d319b37b2997b65681c723cb1e2e1))

## [0.32.4](https://github.com/perkforge/perkforge-platform/compare/v0.32.3...v0.32.4) (2026-11-08)


### Bug Fixes

* **velero:** place Garage on Longhorn worker nodes ([#287](https://github.com/perkforge/perkforge-platform/issues/287)) ([dbf9264](https://github.com/perkforge/perkforge-platform/commit/dbf92646d3aeb41b0bab4c90af2a3c09a5e76c43))

## [0.32.3](https://github.com/perkforge/perkforge-platform/compare/v0.32.2...v0.32.3) (2026-11-08)


### Bug Fixes

* **velero:** assemble empty schedules and native credentials ([#285](https://github.com/perkforge/perkforge-platform/issues/285)) ([0b0ff83](https://github.com/perkforge/perkforge-platform/commit/0b0ff838ecd648e550717c572b308464d0ed696b))

## [0.32.2](https://github.com/perkforge/perkforge-platform/compare/v0.32.1...v0.32.2) (2026-11-08)


### Bug Fixes

* **velero:** handle native CRD and policy API shapes ([#282](https://github.com/perkforge/perkforge-platform/issues/282)) ([9e296c0](https://github.com/perkforge/perkforge-platform/commit/9e296c08917eb2d8a848dfd37f73daf29833806c))

## [0.32.1](https://github.com/perkforge/perkforge-platform/compare/v0.32.0...v0.32.1) (2026-11-08)


### Bug Fixes

* **velero:** keep local object storage HTTPS cluster-private ([#280](https://github.com/perkforge/perkforge-platform/issues/280)) ([6df592d](https://github.com/perkforge/perkforge-platform/commit/6df592d4f91f8182e83822540de35d4183f606e3))

## [0.32.0](https://github.com/perkforge/perkforge-platform/compare/v0.31.3...v0.32.0) (2026-11-08)


### Features

* **velero:** add local baseline and configurable backups ([#255](https://github.com/perkforge/perkforge-platform/issues/255)) ([ec83a2c](https://github.com/perkforge/perkforge-platform/commit/ec83a2c7ac9457be7d8fcccfaf4a7345d3bbca50))

## [0.31.3](https://github.com/perkforge/perkforge-platform/compare/v0.31.2...v0.31.3) (2026-11-08)


### Bug Fixes

* **grafana:** provide memory headroom after repeated OOMs ([#277](https://github.com/perkforge/perkforge-platform/issues/277)) ([172ec94](https://github.com/perkforge/perkforge-platform/commit/172ec94f7709b7b46b2499390e785d701a1830ba))

## [0.31.2](https://github.com/perkforge/perkforge-platform/compare/v0.31.1...v0.31.2) (2026-11-07)


### Bug Fixes

* **grafana:** preserve empty web origins on client toggle ([#275](https://github.com/perkforge/perkforge-platform/issues/275)) ([1ff07af](https://github.com/perkforge/perkforge-platform/commit/1ff07af875c34ce26cbf3527b75038b54d183bef))

## [0.31.1](https://github.com/perkforge/perkforge-platform/compare/v0.31.0...v0.31.1) (2026-11-07)


### Bug Fixes

* **harbor:** use native PKCS1 token signing identities ([#272](https://github.com/perkforge/perkforge-platform/issues/272)) ([2144071](https://github.com/perkforge/perkforge-platform/commit/214407134bd801abb064bb919b564b4c0280ec39))

## [0.31.0](https://github.com/perkforge/perkforge-platform/compare/v0.30.0...v0.31.0) (2026-11-07)


### Features

* **grafana:** prepare cohesive gated SSO activation ([#270](https://github.com/perkforge/perkforge-platform/issues/270)) ([b0c4641](https://github.com/perkforge/perkforge-platform/commit/b0c4641e84f65642cb500cdd5712fc59d71972b6))

## [0.30.0](https://github.com/perkforge/perkforge-platform/compare/v0.29.5...v0.30.0) (2026-11-07)


### Features

* **grafana:** guard dedicated OAuth input delivery ([#253](https://github.com/perkforge/perkforge-platform/issues/253)) ([b5820cf](https://github.com/perkforge/perkforge-platform/commit/b5820cfdfb9090c9335925ad0ca9a47d941336c9))
* **grafana:** prepare bounded disabled client lifecycle ([#252](https://github.com/perkforge/perkforge-platform/issues/252)) ([489bbc6](https://github.com/perkforge/perkforge-platform/commit/489bbc6acdccf8bba10e99c5617670520a950ea1))

## [0.29.5](https://github.com/perkforge/perkforge-platform/compare/v0.29.4...v0.29.5) (2026-11-07)


### Bug Fixes

* **harbor:** preserve empty Keycloak web origins on toggle ([#267](https://github.com/perkforge/perkforge-platform/issues/267)) ([5e0c38e](https://github.com/perkforge/perkforge-platform/commit/5e0c38e0bb0ad146e715d52789ff6fbd49ab5519))

## [0.29.4](https://github.com/perkforge/perkforge-platform/compare/v0.29.3...v0.29.4) (2026-11-07)


### Bug Fixes

* **harbor:** preserve empty unrelated configuration entries ([#265](https://github.com/perkforge/perkforge-platform/issues/265)) ([9dc04f3](https://github.com/perkforge/perkforge-platform/commit/9dc04f36dc434171f1be51b50d80b0dcebccb2bb))

## [0.29.3](https://github.com/perkforge/perkforge-platform/compare/v0.29.2...v0.29.3) (2026-11-07)


### Bug Fixes

* **harbor:** authenticate native system identity verification ([#263](https://github.com/perkforge/perkforge-platform/issues/263)) ([c476fd3](https://github.com/perkforge/perkforge-platform/commit/c476fd322c3a6612457cb307b12a528a3353f227))

## [0.29.2](https://github.com/perkforge/perkforge-platform/compare/v0.29.1...v0.29.2) (2026-11-07)


### Bug Fixes

* **harbor:** allow jobservice PostgreSQL initialization ([#261](https://github.com/perkforge/perkforge-platform/issues/261)) ([3d28773](https://github.com/perkforge/perkforge-platform/commit/3d28773332ab1161eff67b0b2e473c099c3b306c))

## [0.29.1](https://github.com/perkforge/perkforge-platform/compare/v0.29.0...v0.29.1) (2026-11-07)


### Bug Fixes

* **harbor:** repair startup, worker placement and DNS ([#260](https://github.com/perkforge/perkforge-platform/issues/260)) ([2251451](https://github.com/perkforge/perkforge-platform/commit/22514513de100b339761bd001bd32f1ca4c0b06d))
* **harbor:** verify approved CNPG config checksum delta ([#258](https://github.com/perkforge/perkforge-platform/issues/258)) ([7dacd3b](https://github.com/perkforge/perkforge-platform/commit/7dacd3b4baea8e76adef73e7f988a0d532dfb136))

## [0.29.0](https://github.com/perkforge/perkforge-platform/compare/v0.28.0...v0.29.0) (2026-11-07)


### Features

* **harbor:** prepare PostgreSQL, Valkey and SSO rollout ([#251](https://github.com/perkforge/perkforge-platform/issues/251)) ([3ac8f95](https://github.com/perkforge/perkforge-platform/commit/3ac8f95dde9c91d828ee819ac6da8e9552bf044a))

## [0.28.0](https://github.com/perkforge/perkforge-platform/compare/v0.27.0...v0.28.0) (2026-11-07)


### Features

* **harbor:** prepare protected-input registry candidate ([#115](https://github.com/perkforge/perkforge-platform/issues/115)) ([#250](https://github.com/perkforge/perkforge-platform/issues/250)) ([1cef723](https://github.com/perkforge/perkforge-platform/commit/1cef72331c8abbd62e11d26e20e6e23f85d74da9))
* **observability:** prepare native alerts and acceptance checks ([#113](https://github.com/perkforge/perkforge-platform/issues/113)) ([6b9f94d](https://github.com/perkforge/perkforge-platform/commit/6b9f94da97c42491a24e9a4ef0166579bdfc58be))

## [0.27.0](https://github.com/perkforge/perkforge-platform/compare/v0.26.0...v0.27.0) (2026-11-07)


### Features

* **grafana:** prepare disabled SSO client and provider payloads ([#246](https://github.com/perkforge/perkforge-platform/issues/246)) ([a2a1730](https://github.com/perkforge/perkforge-platform/commit/a2a1730aec5eafbeed8ed62b06b4cf6e9286f69b))


### Bug Fixes

* **nextcloud:** capture approved bootstrap access and source selection ([#244](https://github.com/perkforge/perkforge-platform/issues/244)) ([1767c57](https://github.com/perkforge/perkforge-platform/commit/1767c57989d3faefad17e7aaced84a1dbe93e818))
* **nextcloud:** capture exact SSO callback, name and logout settings ([#245](https://github.com/perkforge/perkforge-platform/issues/245)) ([620c8f9](https://github.com/perkforge/perkforge-platform/commit/620c8f9641398f9279b9a3cd5860895da54f946e))

## [0.26.0](https://github.com/perkforge/perkforge-platform/compare/v0.25.0...v0.26.0) (2026-11-07)


### Features

* **nextcloud:** select published SSO enrollment v1.5.0 ([#239](https://github.com/perkforge/perkforge-platform/issues/239)) ([0caba35](https://github.com/perkforge/perkforge-platform/commit/0caba35771f6d5a29e5b6a3444766e7a5b9a1b81))


### Bug Fixes

* **ci:** temporarily pause validation until Nextcloud SSO is complete ([#240](https://github.com/perkforge/perkforge-platform/issues/240)) ([dc7ad39](https://github.com/perkforge/perkforge-platform/commit/dc7ad39097848a1c66833492abe10359cb1d0d41))
* **nextcloud:** select exact local issuer policy through GitOps ([#242](https://github.com/perkforge/perkforge-platform/issues/242)) ([ee3357a](https://github.com/perkforge/perkforge-platform/commit/ee3357a8129ca6212a0c7cedfab9186f8878b780))

## [0.25.0](https://github.com/perkforge/perkforge-platform/compare/v0.24.1...v0.25.0) (2026-11-07)


### Features

* **sso:** add gated Nextcloud client and subject lifecycle ([#217](https://github.com/perkforge/perkforge-platform/issues/217)) ([f6b7f97](https://github.com/perkforge/perkforge-platform/commit/f6b7f97de61a2976e25f836b8d7a4e508ddad79e))

## [0.24.1](https://github.com/perkforge/perkforge-platform/compare/v0.24.0...v0.24.1) (2026-11-07)


### Bug Fixes

* **grafana:** disable inapplicable historical upgrade migration ([#235](https://github.com/perkforge/perkforge-platform/issues/235)) ([1872c70](https://github.com/perkforge/perkforge-platform/commit/1872c70ffd713be9a913760c477c95c267e0d490))

## [0.24.0](https://github.com/perkforge/perkforge-platform/compare/v0.23.5...v0.24.0) (2026-11-07)


### Features

* **monitoring:** prepare scoped lab Grafana HTTPS UI ([#232](https://github.com/perkforge/perkforge-platform/issues/232)) ([e18f068](https://github.com/perkforge/perkforge-platform/commit/e18f06802162f3c8fc36d6c8f38fe62f7070ca6f))

## [0.23.5](https://github.com/perkforge/perkforge-platform/compare/v0.23.4...v0.23.5) (2026-11-06)


### Bug Fixes

* bind limited metrics workloads to existing registry secret ([#229](https://github.com/perkforge/perkforge-platform/issues/229)) ([a45e786](https://github.com/perkforge/perkforge-platform/commit/a45e786f280dc89aa5d2cc9333da4a1501632e7a))

## [0.23.4](https://github.com/perkforge/perkforge-platform/compare/v0.23.3...v0.23.4) (2026-11-06)


### Bug Fixes

* place persistent monitoring consumers on storage workers ([#227](https://github.com/perkforge/perkforge-platform/issues/227)) ([f2741c1](https://github.com/perkforge/perkforge-platform/commit/f2741c112fbda5d15b479acfb6bc0a51e613db18))

## [0.23.3](https://github.com/perkforge/perkforge-platform/compare/v0.23.2...v0.23.3) (2026-11-06)


### Bug Fixes

* **metrics:** preserve Grafana bootstrap and dashboard ownership ([#225](https://github.com/perkforge/perkforge-platform/issues/225)) ([0a95f84](https://github.com/perkforge/perkforge-platform/commit/0a95f848cf7f25275ea514400374a23f70d102b8))

## [0.23.2](https://github.com/perkforge/perkforge-platform/compare/v0.23.1...v0.23.2) (2026-11-06)


### Bug Fixes

* **gitlab:** suppress unselected discovered ServiceMonitors ([#223](https://github.com/perkforge/perkforge-platform/issues/223)) ([72dd82e](https://github.com/perkforge/perkforge-platform/commit/72dd82eace48797f7642c89be623bcdd77908eb4))

## [0.23.1](https://github.com/perkforge/perkforge-platform/compare/v0.23.0...v0.23.1) (2026-11-06)


### Bug Fixes

* **gitlab:** reduce home-lab toolbox CPU reservation ([#220](https://github.com/perkforge/perkforge-platform/issues/220)) ([b75acc9](https://github.com/perkforge/perkforge-platform/commit/b75acc960d91a89b21cd842304ef8bb963f4efbe))

## [0.23.0](https://github.com/perkforge/perkforge-platform/compare/v0.22.2...v0.23.0) (2026-11-06)


### Features

* **logging:** prepare backend-only pilot without monitoring runtime ([#211](https://github.com/perkforge/perkforge-platform/issues/211)) ([7cafc38](https://github.com/perkforge/perkforge-platform/commit/7cafc38f472008c7170153a35881049127e800b1))
* **observability:** carry limited pilot roots onto main ([#216](https://github.com/perkforge/perkforge-platform/issues/216)) ([94ad924](https://github.com/perkforge/perkforge-platform/commit/94ad924a36374e5d00569aa472ea0a93b81439a4))


### Bug Fixes

* **monitoring:** scope system metric Service installer access ([db2ac7b](https://github.com/perkforge/perkforge-platform/commit/db2ac7b4bae67be97a7ee0b8590b9b6a192852b3))

## [0.22.2](https://github.com/perkforge/perkforge-platform/compare/v0.22.1...v0.22.2) (2026-11-06)


### Bug Fixes

* **nextcloud:** select guarded cron activation enrollment ([84ee100](https://github.com/perkforge/perkforge-platform/commit/84ee10093a1864ff34ac9d97878ca24317a45374))
* **nextcloud:** select guarded cron activation enrollment ([d36ab3d](https://github.com/perkforge/perkforge-platform/commit/d36ab3dccdf6b4042a19601db4df82cf2930c58a))

## [0.22.1](https://github.com/perkforge/perkforge-platform/compare/v0.22.0...v0.22.1) (2026-11-06)


### Bug Fixes

* **nextcloud:** select released disabled cron correction ([12317e4](https://github.com/perkforge/perkforge-platform/commit/12317e4191fa560360ccb0efaad4f13cd47804ec))
* **nextcloud:** select released disabled cron correction ([5bbc17f](https://github.com/perkforge/perkforge-platform/commit/5bbc17f96e84ca512c3e6c2370cb92f1bb330260))

## [0.22.0](https://github.com/perkforge/perkforge-platform/compare/v0.21.0...v0.22.0) (2026-11-06)


### Features

* **observability:** gate immutable logging pilot input delivery ([c2afe2f](https://github.com/perkforge/perkforge-platform/commit/c2afe2f14de99db8658a4c8c5ce13dd9fd83822b))


### Bug Fixes

* **observability:** restrict logging inputs to the pinned CA ([c25ada3](https://github.com/perkforge/perkforge-platform/commit/c25ada355a7e0ebba9dea7435feb923435d591e1))

## [0.21.0](https://github.com/perkforge/perkforge-platform/compare/v0.20.0...v0.21.0) (2026-11-06)


### Features

* **observability:** prepare scoped authenticated logging ([c27072f](https://github.com/perkforge/perkforge-platform/commit/c27072fe64945f79db1f4f66b0278f3d204c0579))


### Bug Fixes

* **nextcloud:** pin published CNPG authority enrollment ([#204](https://github.com/perkforge/perkforge-platform/issues/204)) ([7adb782](https://github.com/perkforge/perkforge-platform/commit/7adb782bb13d70684cac65a9a6dbab20884de589))
* **nextcloud:** scope shared CNPG watch to enrolled namespaces ([12fffa3](https://github.com/perkforge/perkforge-platform/commit/12fffa3e7c6acf4bb3c9f8d317548310161b6959))
* **nextcloud:** scope shared CNPG watch to enrolled namespaces ([bf4678d](https://github.com/perkforge/perkforge-platform/commit/bf4678dd3e3c8fe7d03f56817939885bc5dcb5e1))

## [0.20.0](https://github.com/perkforge/perkforge-platform/compare/v0.19.0...v0.20.0) (2026-11-06)


### Features

* **dns:** add guarded Nextcloud record maintenance ([#201](https://github.com/perkforge/perkforge-platform/issues/201)) ([1986213](https://github.com/perkforge/perkforge-platform/commit/1986213461bb25eb29724cc1f9d2b534023dfaf6))
* **monitoring:** implement inactive metrics and Grafana foundations ([#111](https://github.com/perkforge/perkforge-platform/issues/111)) ([e17b5e7](https://github.com/perkforge/perkforge-platform/commit/e17b5e75d7cc040dc58ec9e02556708cbc9e1977))
* **nextcloud:** add release-pinned platform data-stage selection ([#200](https://github.com/perkforge/perkforge-platform/issues/200)) ([be40d77](https://github.com/perkforge/perkforge-platform/commit/be40d77e69252ecdeee9004c8c0ed7b49d37fe80))
* **observability:** review architecture and bounded inactive values ([#108](https://github.com/perkforge/perkforge-platform/issues/108)) ([fc2ad86](https://github.com/perkforge/perkforge-platform/commit/fc2ad8616fc2f1e7d415b1249dc463e8715f7315))


### Bug Fixes

* **release:** record the actual published release commit ([#197](https://github.com/perkforge/perkforge-platform/issues/197)) ([c47a7f9](https://github.com/perkforge/perkforge-platform/commit/c47a7f949a27dd561a72da19d2eea1aaf0e2ff89))

## [0.19.0](https://github.com/perkforge/perkforge-platform/compare/v0.18.4...v0.19.0) (2026-11-05)


### Features

* **infrastructure:** persist guarded UUID mounts for worker storage ([#194](https://github.com/perkforge/perkforge-platform/issues/194)) ([4bc1133](https://github.com/perkforge/perkforge-platform/commit/4bc1133a43cb814f37bf8ca06106c194e43303ce))
* **longhorn:** add dedicated and single-excess storage tiers ([#184](https://github.com/perkforge/perkforge-platform/issues/184)) ([0b8dfd4](https://github.com/perkforge/perkforge-platform/commit/0b8dfd44930afc32dbbd9bbfcc0f747aa4c24c35))

## [0.18.4](https://github.com/perkforge/perkforge-platform/compare/v0.18.3...v0.18.4) (2026-11-05)


### Bug Fixes

* **runner:** writable Git home and worker-only jobs ([#190](https://github.com/perkforge/perkforge-platform/issues/190)) ([b6aa1f6](https://github.com/perkforge/perkforge-platform/commit/b6aa1f6b089a14426a3a54121c6186ee7e3c5437))

## [0.18.3](https://github.com/perkforge/perkforge-platform/compare/v0.18.2...v0.18.3) (2026-11-05)


### Bug Fixes

* **runner:** complete restricted init context and audit handoff ([#189](https://github.com/perkforge/perkforge-platform/issues/189)) ([98866cf](https://github.com/perkforge/perkforge-platform/commit/98866cf561e4b923991de121a12d45d17cfcf492))
* **runner:** preserve foundation namespace ownership ([#187](https://github.com/perkforge/perkforge-platform/issues/187)) ([ee7ebc9](https://github.com/perkforge/perkforge-platform/commit/ee7ebc9c57ce02ea741baf25c5f4d91eacc12635))

## [0.18.2](https://github.com/perkforge/perkforge-platform/compare/v0.18.1...v0.18.2) (2026-11-05)


### Bug Fixes

* **gitlab-runner:** accept routable v1 authentication tokens ([#185](https://github.com/perkforge/perkforge-platform/issues/185)) ([8e0b698](https://github.com/perkforge/perkforge-platform/commit/8e0b698cacecb576c5d19e5c2a67027946531968))

## [0.18.1](https://github.com/perkforge/perkforge-platform/compare/v0.18.0...v0.18.1) (2026-11-05)


### Bug Fixes

* **gitlab-runner:** meet native minimum runner timeout ([#182](https://github.com/perkforge/perkforge-platform/issues/182)) ([953de3e](https://github.com/perkforge/perkforge-platform/commit/953de3e356c99776583b94ddad9f18976d163d6a))

## [0.18.0](https://github.com/perkforge/perkforge-platform/compare/v0.17.11...v0.18.0) (2026-11-05)


### Features

* **gitlab:** verify named SSO and document existing runner activation ([#180](https://github.com/perkforge/perkforge-platform/issues/180)) ([d644479](https://github.com/perkforge/perkforge-platform/commit/d644479e59f031fea936f33ac441607fc0ec887f))

## [0.17.11](https://github.com/perkforge/perkforge-platform/compare/v0.17.10...v0.17.11) (2026-11-05)


### Bug Fixes

* **gitlab:** allow recommended memory for two Puma workers ([#178](https://github.com/perkforge/perkforge-platform/issues/178)) ([62f5afa](https://github.com/perkforge/perkforge-platform/commit/62f5afa020aaf321d26dcf8aeeadc4ddde58b87c))

## [0.17.10](https://github.com/perkforge/perkforge-platform/compare/v0.17.9...v0.17.10) (2026-11-05)


### Bug Fixes

* **gitlab:** mount PostgreSQL CA outside read-only configuration ([#176](https://github.com/perkforge/perkforge-platform/issues/176)) ([bfb3894](https://github.com/perkforge/perkforge-platform/commit/bfb3894f93d7af83c81d83c9db3dab8cf6795ad7))

## [0.17.9](https://github.com/perkforge/perkforge-platform/compare/v0.17.8...v0.17.9) (2026-11-05)


### Bug Fixes

* **gitlab:** preserve partial state after failed Helm actions ([#174](https://github.com/perkforge/perkforge-platform/issues/174)) ([9e47e7f](https://github.com/perkforge/perkforge-platform/commit/9e47e7fd31e0a11333017d9b992de5adcd65f858))

## [0.17.8](https://github.com/perkforge/perkforge-platform/compare/v0.17.7...v0.17.8) (2026-11-04)


### Bug Fixes

* **gitlab:** reference pull Secret for hooks and workloads ([#172](https://github.com/perkforge/perkforge-platform/issues/172)) ([3428921](https://github.com/perkforge/perkforge-platform/commit/34289219e925c2b3c71c1925d3a107761062fff6))

## [0.17.7](https://github.com/perkforge/perkforge-platform/compare/v0.17.6...v0.17.7) (2026-11-04)


### Bug Fixes

* **gitlab:** preserve external namespace ownership ([#170](https://github.com/perkforge/perkforge-platform/issues/170)) ([4a7d392](https://github.com/perkforge/perkforge-platform/commit/4a7d3926a3c43325237a9864220dd5ff5cf9af41))

## [0.17.6](https://github.com/perkforge/perkforge-platform/compare/v0.17.5...v0.17.6) (2026-11-04)


### Bug Fixes

* **gitlab:** constrain Gitaly to storage workers ([#168](https://github.com/perkforge/perkforge-platform/issues/168)) ([dc7b902](https://github.com/perkforge/perkforge-platform/commit/dc7b902a1faecb0f9e6e6c6f4910ed722ef60c2c))

## [0.17.5](https://github.com/perkforge/perkforge-platform/compare/v0.17.4...v0.17.5) (2026-11-04)


### Bug Fixes

* **gitlab:** delegate namespaced Flux Pod health reads ([#166](https://github.com/perkforge/perkforge-platform/issues/166)) ([97bbb21](https://github.com/perkforge/perkforge-platform/commit/97bbb21bb6de9e07ec5de5e836cdcb1e990394e8))

## [0.17.4](https://github.com/perkforge/perkforge-platform/compare/v0.17.3...v0.17.4) (2026-11-04)


### Bug Fixes

* **gitlab:** validate Garage layout before object bootstrap ([#164](https://github.com/perkforge/perkforge-platform/issues/164)) ([307d831](https://github.com/perkforge/perkforge-platform/commit/307d8316fc6efef3c66fc8d82a223856de09b3d8))

## [0.17.3](https://github.com/perkforge/perkforge-platform/compare/v0.17.2...v0.17.3) (2026-11-04)


### Bug Fixes

* **gitlab:** launch the pinned Garage executable explicitly ([#162](https://github.com/perkforge/perkforge-platform/issues/162)) ([37ad288](https://github.com/perkforge/perkforge-platform/commit/37ad28884139478f93f08ca95b31d7bb00b20bf5))

## [0.17.2](https://github.com/perkforge/perkforge-platform/compare/v0.17.1...v0.17.2) (2026-11-04)


### Bug Fixes

* **gitlab:** guard data placement DNS maintenance and CA lifecycle ([#160](https://github.com/perkforge/perkforge-platform/issues/160)) ([c13ca06](https://github.com/perkforge/perkforge-platform/commit/c13ca06873ec1a0c868f0d631a870c62ae6dd6a8))

## [0.17.1](https://github.com/perkforge/perkforge-platform/compare/v0.17.0...v0.17.1) (2026-11-04)


### Bug Fixes

* **gitlab:** place persistent Valkey on storage workers ([#158](https://github.com/perkforge/perkforge-platform/issues/158)) ([649f0c7](https://github.com/perkforge/perkforge-platform/commit/649f0c77e413b0184ab29fc9ee55fbfdce502916))

## [0.17.0](https://github.com/perkforge/perkforge-platform/compare/v0.16.1...v0.17.0) (2026-11-03)


### Features

* **gitlab:** prepare coordinated SSO, data services and runner ([#156](https://github.com/perkforge/perkforge-platform/issues/156)) ([7aeb06c](https://github.com/perkforge/perkforge-platform/commit/7aeb06c3c69d828159af15514ab94251ce28bd94))

## [0.16.1](https://github.com/perkforge/perkforge-platform/compare/v0.16.0...v0.16.1) (2026-11-03)


### Bug Fixes

* **openbao:** allow bounded SSO self-session and UI operations ([#153](https://github.com/perkforge/perkforge-platform/issues/153)) ([701edff](https://github.com/perkforge/perkforge-platform/commit/701edffb1a7ab2112303816c80e09950da2f21f9))

## [0.16.0](https://github.com/perkforge/perkforge-platform/compare/v0.15.2...v0.16.0) (2026-11-03)


### Features

* **sso:** prepare gated OpenBao data engines and remaining app acceptance ([#145](https://github.com/perkforge/perkforge-platform/issues/145)) ([f579707](https://github.com/perkforge/perkforge-platform/commit/f5797074f9704374b1366a1db7cfbd740b2d80cd))


### Bug Fixes

* **rancher:** validate pinned chart CA mount contract ([#150](https://github.com/perkforge/perkforge-platform/issues/150)) ([dc1470b](https://github.com/perkforge/perkforge-platform/commit/dc1470bee13811d394ed0f6d6b4d0e510669f0d1))


### Performance Improvements

* **ci:** parallelize complete offline regression suites ([#149](https://github.com/perkforge/perkforge-platform/issues/149)) ([051e2d4](https://github.com/perkforge/perkforge-platform/commit/051e2d40af7d059187de549478538fb4279d2020))
* **ci:** select conservative offline suites and remove duplicate triggers ([#146](https://github.com/perkforge/perkforge-platform/issues/146)) ([79e6967](https://github.com/perkforge/perkforge-platform/commit/79e6967dd08288e49fee045fd2b29f54ff0feb3f))

## [0.15.2](https://github.com/perkforge/perkforge-platform/compare/v0.15.1...v0.15.2) (2026-11-03)


### Bug Fixes

* **headlamp:** validate pinned OIDC arguments and enable PKCE ([#144](https://github.com/perkforge/perkforge-platform/issues/144)) ([0186c34](https://github.com/perkforge/perkforge-platform/commit/0186c348f064d9e72f12dc76e4393c0e6e8e1182))

## [0.15.1](https://github.com/perkforge/perkforge-platform/compare/v0.15.0...v0.15.1) (2026-11-03)


### Bug Fixes

* **identity:** accept canonical empty mapper prefix ([#142](https://github.com/perkforge/perkforge-platform/issues/142)) ([5366e1a](https://github.com/perkforge/perkforge-platform/commit/5366e1ab4f2d88fa7a6d180773a08cd4c2d09c86))

## [0.15.0](https://github.com/perkforge/perkforge-platform/compare/v0.14.0...v0.15.0) (2026-11-03)


### Features

* **headlamp:** add gated SSO selection stage ([#140](https://github.com/perkforge/perkforge-platform/issues/140)) ([67b21af](https://github.com/perkforge/perkforge-platform/commit/67b21af75cad7336ccdb6f5fb07ca511fe410f6c))
* **headlamp:** gate API OIDC maintenance and HTTPS routing ([#141](https://github.com/perkforge/perkforge-platform/issues/141)) ([400e106](https://github.com/perkforge/perkforge-platform/commit/400e106816408ec53281c15cd31ec51829b5dd2f))
* **headlamp:** preserve temporary admin acceptance and cleanup ([#124](https://github.com/perkforge/perkforge-platform/issues/124)) ([66ac544](https://github.com/perkforge/perkforge-platform/commit/66ac5448b5ca489347ef4596344f386aaa794462))
* **identity:** add gated PerkForge realm and empty role groups ([#127](https://github.com/perkforge/perkforge-platform/issues/127)) ([f2fa519](https://github.com/perkforge/perkforge-platform/commit/f2fa519434973197a12008805324c08d97a3644d))
* **identity:** prepare full PerkForge realm administration ([#135](https://github.com/perkforge/perkforge-platform/issues/135)) ([8b22f4f](https://github.com/perkforge/perkforge-platform/commit/8b22f4f957d5e24e7f27cf4cf153539299a8e7b7))
* **identity:** prepare gated IL2 human TOTP enrollment ([#129](https://github.com/perkforge/perkforge-platform/issues/129)) ([8290d22](https://github.com/perkforge/perkforge-platform/commit/8290d2233e5582d2170d1646dca2ada1a0f1edd2))
* prepare coordinated platform application SSO ([#139](https://github.com/perkforge/perkforge-platform/issues/139)) ([8214a16](https://github.com/perkforge/perkforge-platform/commit/8214a169a38046d1dbccddbd95244cf3d9a4558c))


### Bug Fixes

* **identity:** declare managed ownership markers and guard partial resume ([#131](https://github.com/perkforge/perkforge-platform/issues/131)) ([0da7395](https://github.com/perkforge/perkforge-platform/commit/0da7395eb6bf327538bcae76c4435dc770d5de49))
* **identity:** resolve nested authentication metadata by execution flow ID ([#132](https://github.com/perkforge/perkforge-platform/issues/132)) ([4dd6481](https://github.com/perkforge/perkforge-platform/commit/4dd6481b351ed2f254c09df490e241d1d8b11c18))
* **identity:** validate the built-in realm-admin composite graph ([#136](https://github.com/perkforge/perkforge-platform/issues/136)) ([9398fb5](https://github.com/perkforge/perkforge-platform/commit/9398fb589326765606ca36ba1f3716827aeb62e8))
* validate approved post-grant realm admin representation ([#137](https://github.com/perkforge/perkforge-platform/issues/137)) ([e7cac52](https://github.com/perkforge/perkforge-platform/commit/e7cac52fcc328249de9ef7d704757d6484996b4a))

## [0.14.0](https://github.com/perkforge/perkforge-platform/compare/v0.13.0...v0.14.0) (2026-11-01)


### Features

* **openbao:** add exact-SNI TLS passthrough candidate ([#123](https://github.com/perkforge/perkforge-platform/issues/123)) ([07b3d6b](https://github.com/perkforge/perkforge-platform/commit/07b3d6b37667d08e7cfcdd2fe2aa48c4728f5cdf))
* **openbao:** preserve guarded initialization and custody procedure ([#121](https://github.com/perkforge/perkforge-platform/issues/121)) ([23791c3](https://github.com/perkforge/perkforge-platform/commit/23791c3470ac48872253ef2c8a9f6f20066b115c))

## [0.13.0](https://github.com/perkforge/perkforge-platform/compare/v0.12.0...v0.13.0) (2026-11-01)


### Features

* **auth:** review six-role mappings and ongoing authorization evidence ([#107](https://github.com/perkforge/perkforge-platform/issues/107)) ([742c299](https://github.com/perkforge/perkforge-platform/commit/742c2995715448f2ea90748a9c57bae0a211f665))
* **headlamp:** select token-only initial UI stage ([#104](https://github.com/perkforge/perkforge-platform/issues/104)) ([e750571](https://github.com/perkforge/perkforge-platform/commit/e75057197111a7898ec438d2f1e79bd9fe0a54fe))
* **keycloak:** select isolated master-admin deployment stage ([#106](https://github.com/perkforge/perkforge-platform/issues/106)) ([7578d78](https://github.com/perkforge/perkforge-platform/commit/7578d78fd02c4ae47d54fe5ca1b8c35cfc8ca65d))
* **openbao:** prepare TLS-required initial token administration ([#103](https://github.com/perkforge/perkforge-platform/issues/103)) ([d42e360](https://github.com/perkforge/perkforge-platform/commit/d42e36090d7605680cce6d6f1e62efd0f3ece83c))
* **platform:** gate app selection through ordered release stages ([#119](https://github.com/perkforge/perkforge-platform/issues/119)) ([59ead1f](https://github.com/perkforge/perkforge-platform/commit/59ead1f5e329001775fd1cd2e687dbe2516a434e))


### Bug Fixes

* **keycloak:** pin verified Iron Bank 26.8.1 security image ([#120](https://github.com/perkforge/perkforge-platform/issues/120)) ([d3059db](https://github.com/perkforge/perkforge-platform/commit/d3059db89b0decff5b4704645663cdbff6da1b4c))

## [0.12.0](https://github.com/perkforge/perkforge-platform/compare/v0.11.3...v0.12.0) (2026-11-01)


### Features

* **rancher:** select local-admin Big Bang stage ([#100](https://github.com/perkforge/perkforge-platform/issues/100)) ([870d042](https://github.com/perkforge/perkforge-platform/commit/870d04296b51bb1cf285e831f503260cbb9f5d6d))

## [0.11.3](https://github.com/perkforge/perkforge-platform/compare/v0.11.2...v0.11.3) (2026-11-01)


### Bug Fixes

* **longhorn:** authorize reviewed diagnostic role binding ([#97](https://github.com/perkforge/perkforge-platform/issues/97)) ([1247b0c](https://github.com/perkforge/perkforge-platform/commit/1247b0cde315fbeab9e075fa5e3e4cd60344903c))

## [0.11.2](https://github.com/perkforge/perkforge-platform/compare/v0.11.1...v0.11.2) (2026-11-01)


### Bug Fixes

* **longhorn:** permit installer chart ClusterRole lookup ([#93](https://github.com/perkforge/perkforge-platform/issues/93)) ([d7d228c](https://github.com/perkforge/perkforge-platform/commit/d7d228cdbaef00a013bafef5a53bb6392791e2d5))

## [0.11.1](https://github.com/perkforge/perkforge-platform/compare/v0.11.0...v0.11.1) (2026-11-01)


### Bug Fixes

* **bootstrap:** make Flux registry delivery repeatable ([#91](https://github.com/perkforge/perkforge-platform/issues/91)) ([57f8d04](https://github.com/perkforge/perkforge-platform/commit/57f8d044a1c92210960f0df95fd6802914c31065))

## [0.11.0](https://github.com/perkforge/perkforge-platform/compare/v0.10.0...v0.11.0) (2026-10-31)


### Features

* **bootstrap:** enable Longhorn-only GitOps desired state ([#89](https://github.com/perkforge/perkforge-platform/issues/89)) ([1b2264d](https://github.com/perkforge/perkforge-platform/commit/1b2264db30c79f75822540ffe01daf4455ab9a64))

## [0.10.0](https://github.com/perkforge/perkforge-platform/compare/v0.9.0...v0.10.0) (2026-10-31)


### Features

* **bootstrap:** stage Longhorn-first platform rollout ([#87](https://github.com/perkforge/perkforge-platform/issues/87)) ([e441dc6](https://github.com/perkforge/perkforge-platform/commit/e441dc682c4f9575c27cdf52eb7fca5784f949d8))

## [0.9.0](https://github.com/perkforge/perkforge-platform/compare/v0.8.0...v0.9.0) (2026-10-31)


### Features

* **platform:** establish physical RKE2 foundations and staged Big Bang bootstrap ([#84](https://github.com/perkforge/perkforge-platform/issues/84)) ([036f1ec](https://github.com/perkforge/perkforge-platform/commit/036f1ecbdac4a25f32aabdd24a2e5cc0c992180f))


### Bug Fixes

* **ci:** align published selection chain and reject incompatible releases ([#85](https://github.com/perkforge/perkforge-platform/issues/85)) ([3da9ad3](https://github.com/perkforge/perkforge-platform/commit/3da9ad3f9088f4fc25dba51405bc67f27eaa8287))

## [0.8.0](https://github.com/perkforge/perkforge-platform/compare/v0.7.0...v0.8.0) (2026-10-30)


### Features

* organize Big Bang bootstrap for physical clusters ([#73](https://github.com/perkforge/perkforge-platform/issues/73)) ([fb365ba](https://github.com/perkforge/perkforge-platform/commit/fb365bac8a7023e9cf0c8025ed7db93c0df2a4d1))

## [0.7.0](https://github.com/perkforge/perkforge-platform/compare/v0.6.0...v0.7.0) (2026-10-29)


### Features

* **gitops:** select local enrollment activation release ([#71](https://github.com/perkforge/perkforge-platform/issues/71)) ([a025980](https://github.com/perkforge/perkforge-platform/commit/a025980b1f5bef3756e1949d8ef4c764b18195d2))

## [0.6.0](https://github.com/perkforge/perkforge-platform/compare/v0.5.3...v0.6.0) (2026-10-29)


### Features

* **gitops:** prepare paused local tenant enrollment stage ([#69](https://github.com/perkforge/perkforge-platform/issues/69)) ([71c3d3b](https://github.com/perkforge/perkforge-platform/commit/71c3d3bff5b698be1a30ccee0b238f1f07e6726f))

## [0.5.3](https://github.com/perkforge/perkforge-platform/compare/v0.5.2...v0.5.3) (2026-10-29)


### Bug Fixes

* **platform:** grant platform admins full cluster authority ([#65](https://github.com/perkforge/perkforge-platform/issues/65)) ([ba50bcf](https://github.com/perkforge/perkforge-platform/commit/ba50bcf11e6e04b1a1aeaf63f8e95537773e57bb))

## [0.5.2](https://github.com/perkforge/perkforge-platform/compare/v0.5.1...v0.5.2) (2026-10-29)


### Bug Fixes

* avoid duplicate RKE2 OIDC CA mount ([#63](https://github.com/perkforge/perkforge-platform/issues/63)) ([c6543f1](https://github.com/perkforge/perkforge-platform/commit/c6543f18b7981653d28c6fea4655dbeae1f2a6ee))

## [0.5.1](https://github.com/perkforge/perkforge-platform/compare/v0.5.0...v0.5.1) (2026-10-29)


### Bug Fixes

* allow scoped Keycloak chart Secret lookups ([#61](https://github.com/perkforge/perkforge-platform/issues/61)) ([8250337](https://github.com/perkforge/perkforge-platform/commit/825033708d126bf2220689c913694d0dfe37c77a))

## [0.5.0](https://github.com/perkforge/perkforge-platform/compare/v0.4.0...v0.5.0) (2026-10-28)


### Features

* prepare local Keycloak-backed Headlamp login ([#59](https://github.com/perkforge/perkforge-platform/issues/59)) ([33eacd8](https://github.com/perkforge/perkforge-platform/commit/33eacd84c06b7cd6a1f1f1686c45787b9a34d7a6))

## [0.4.0](https://github.com/perkforge/perkforge-platform/compare/v0.3.0...v0.4.0) (2026-10-28)


### Features

* **local:** add scoped Headlamp Big Bang smoke stage ([#58](https://github.com/perkforge/perkforge-platform/issues/58)) ([6b3f0e2](https://github.com/perkforge/perkforge-platform/commit/6b3f0e2a6edb3aceaac5aee2b347c0a9456fad6d))
* **local:** prepare RKE2-only Big Bang trial provisioning ([#56](https://github.com/perkforge/perkforge-platform/issues/56)) ([0498a94](https://github.com/perkforge/perkforge-platform/commit/0498a94f0fdfe3be57fc3afa9ac7cd0e0304a08c))

## [0.3.0](https://github.com/perkforge/perkforge-platform/compare/v0.2.0...v0.3.0) (2026-10-28)


### Features

* **local:** propose tiny resource profile and staged startup trial ([#54](https://github.com/perkforge/perkforge-platform/issues/54)) ([6abfc7c](https://github.com/perkforge/perkforge-platform/commit/6abfc7c830d8c1e3db0743e13127ec66c8fa5fbc))

## [0.2.0](https://github.com/perkforge/perkforge-platform/compare/v0.1.1...v0.2.0) (2026-10-28)


### Features

* **preflight:** inventory pinned minimal Big Bang stack and local capacity ([#52](https://github.com/perkforge/perkforge-platform/issues/52)) ([91c59fd](https://github.com/perkforge/perkforge-platform/commit/91c59fd21533e143679cc0acd80bb97c63828bfb))

## [0.1.1](https://github.com/perkforge/perkforge-platform/compare/v0.1.0...v0.1.1) (2026-10-28)


### Bug Fixes

* **gitops:** select published tags for platform bootstrap chain ([#50](https://github.com/perkforge/perkforge-platform/issues/50)) ([ca5da29](https://github.com/perkforge/perkforge-platform/commit/ca5da29f51c2c5de584dc4e26ef427e7df52c92c))

## 0.1.0 (2026-10-28)


### Features

* **release:** add reviewed configuration version tags ([#48](https://github.com/perkforge/perkforge-platform/issues/48)) ([f0ee760](https://github.com/perkforge/perkforge-platform/commit/f0ee7605938e279cd1b833fe4528e8a35a3615d9))
