from app.ai.accounting import make_usage
from app.ai.interfaces import LLMResult, Msg
from app.ai.registry import ProviderRegistry
from app.ai.router import AIRouter, ProfileConfig
from app.cache.memory import MemoryCache


class CountingProvider:
    def __init__(self, name):
        self.name = name
        self.calls = 0

    def complete(self, *, system, messages, model, **kw):
        self.calls += 1
        return LLMResult(
            text=f"answer-{self.calls}",
            provider=self.name,
            model=model,
            usage=make_usage(input_tokens=10, output_tokens=5, cost_usd=0.01),
        )


def _router(cache, *, cache_on):
    reg = ProviderRegistry()
    prov = CountingProvider("anthropic")
    reg.register(prov)
    profiles = {"p": ProfileConfig("llm", "anthropic/m", cache=cache_on)}
    return AIRouter(reg, profiles, cache=cache), prov


def test_cache_hit_skips_second_provider_call():
    cache = MemoryCache()
    router, prov = _router(cache, cache_on=True)
    kw = dict(system="s", messages=[Msg("user", "le chat")])
    first = router.run("p", **kw)
    second = router.run("p", **kw)
    assert prov.calls == 1  # second served from cache
    assert second.text == first.text
    assert second.usage.cost_usd == 0.0  # cached hit costs nothing


def test_no_cache_when_profile_opts_out():
    cache = MemoryCache()
    router, prov = _router(cache, cache_on=False)
    kw = dict(system="s", messages=[Msg("user", "x")])
    router.run("p", **kw)
    router.run("p", **kw)
    assert prov.calls == 2


def test_different_input_is_a_cache_miss():
    cache = MemoryCache()
    router, prov = _router(cache, cache_on=True)
    router.run("p", system="s", messages=[Msg("user", "a")])
    router.run("p", system="s", messages=[Msg("user", "b")])
    assert prov.calls == 2
