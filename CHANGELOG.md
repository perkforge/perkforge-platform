# Changelog

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
