import pytest
import numpy as np

from ..se_obs import SEObs
from ..simple_sim import Sim


def test_simple_sim_smoke():
    sim = Sim(rng=10, gals_kws={'density': 10})
    data = sim.gen_sim()
    assert len(data) == sim.n_bands
    assert sim.star_density == 0.0

    for band in sim.bands:
        assert len(data[band]) == sim.epochs_per_band
        for epoch in range(sim.epochs_per_band):
            epoch_obs = data[band][epoch]
            assert isinstance(epoch_obs, SEObs)
            assert epoch_obs.noise is not None


def test_simple_sim_wldeblend():
    try:
        sim = Sim(
            rng=101,
            gals_kws={'density': 10},
            gals_type='wldeblend',
        )
        sim.gen_sim()
    except OSError:
        # the catalog is probably not present
        pass


def test_simple_sim_fixed_stars():
    sim = Sim(
        rng=120,
        gals_kws={'density': 10},
        stars=True,
    )
    sim.gen_sim()


def test_simple_sim_sample_stars():
    try:
        sim = Sim(
            gals_kws={'density': 10},
            rng=335,
            gals_type='wldeblend',
            stars=True,
            stars_type='sample',
        )
        sim.gen_sim()
    except OSError:
        # the catalog is probably not present
        pass


def test_simple_sim_sample_star_density():
    min_density = 2
    max_density = 20
    try:
        sim = Sim(
            gals_kws={'density': 10},
            rng=335,
            gals_type='wldeblend',
            stars=True,
            stars_kws={
                'type': 'sample',
                'density': {
                    'min_density': min_density,
                    'max_density': max_density,
                }
            },
        )
        sim.gen_sim()

        assert min_density < sim.star_density < max_density
    except OSError:
        # the catalog is probably not present
        pass


def test_simple_sim_sample_star_minmag_smoke():
    try:
        sim = Sim(
            gals_kws={'density': 10},
            rng=335,
            gals_type='wldeblend',
            stars=True,
            stars_kws={
                'type': 'sample',
                'min_mag': 20,
            },
        )
        sim.gen_sim()
    except OSError:
        # the catalog is probably not present
        pass


def test_simple_sim_cap_radius_smoke():
    sim = Sim(rng=10, cap_radius=1, gals_kws={'density': 10})
    assert sim.buff == 0.0

    data = sim.gen_sim()
    assert len(data) == sim.n_bands
    for band in sim.bands:
        assert len(data[band]) == sim.epochs_per_band
        for epoch in range(sim.epochs_per_band):
            epoch_obs = data[band][epoch]
            assert isinstance(epoch_obs, SEObs)
            assert epoch_obs.noise is not None


def test_simple_sim_noise():
    sim = Sim(rng=10, gals_kws={'density': 10})
    data = sim.gen_sim()
    for band in sim.bands:
        for epoch in range(sim.epochs_per_band):
            epoch_obs = data[band][epoch]

            assert epoch_obs.noise is not None

            nvar = epoch_obs.noise.array.var()
            expected_var = 1/epoch_obs.weight.array[0, 0]
            assert abs(nvar/expected_var-1) < 0.015


def test_simple_sim_double_call_raises():
    sim = Sim(rng=10, gals_kws={'density': 10})
    sim.gen_sim()
    with pytest.raises(RuntimeError):
        sim.gen_sim()


def test_simple_sim_psf_smoke():
    sim = Sim(rng=10, gals_kws={'density': 10})
    data = sim.gen_sim()
    assert len(data) == sim.n_bands
    for band in sim.bands:
        assert len(data[band]) == sim.epochs_per_band
        for epoch in range(sim.epochs_per_band):
            # make sure this call works
            data[band][epoch].get_psf(10, 3)


def test_simple_sim_psf_center():
    sim = Sim(rng=10, gals_kws={'density': 10})
    data = sim.gen_sim()
    se_obs = data[sim.bands[0]][0]

    psf1 = se_obs.get_psf(10, 3, center_psf=False)
    psf2 = se_obs.get_psf(10, 3, center_psf=True)
    assert np.array_equal(psf1.array, psf2.array)
    assert np.allclose(psf1.array, psf1.array.T)
    assert np.allclose(psf2.array, psf2.array.T)

    psf1nc = se_obs.get_psf(10.3, 3.25, center_psf=False)
    psf2nc = se_obs.get_psf(10.3, 3.25, center_psf=True)
    assert not np.array_equal(psf1nc.array, psf2nc.array)
    assert not np.allclose(psf1nc.array, psf1nc.array.T)
    assert np.allclose(psf2nc.array, psf2nc.array.T)
    assert np.allclose(psf2nc.array, psf1.array)

    x = 10.2
    y = 3.75
    _, offset = se_obs.get_psf(x, y, center_psf=False, get_offset=True)
    assert offset.x == x - int(x+0.5)
    assert offset.y == y - int(y+0.5)

    if False:
        import matplotlib.pyplot as plt
        fig, axs = plt.subplots(nrows=1, ncols=2, figsize=(16, 8))
        axs[0].imshow(psf1nc.array)
        axs[0].set_title('not centered')

        axs[1].imshow(psf2nc.array)
        axs[1].set_title('centered')

        assert False


def test_simple_sim_psf_shape():
    """
    test we get roughly the right psf shape out. cannot expect detailed
    agreement due to pixelization
    """
    import galsim

    shear = galsim.Shear(g1=0.2, g2=-0.2)
    sim = Sim(
        rng=10,
        psf_kws={'g1': shear.g1, 'g2': shear.g2},
        gals_kws={'density': 10},
    )
    data = sim.gen_sim()
    se_obs = data[sim.bands[0]][0]

    psf = se_obs.get_psf(10, 3, center_psf=True).array

    cen = (np.array(psf.shape)-1)/2
    ny, nx = psf.shape
    rows, cols = np.mgrid[
        0:ny,
        0:nx,
    ]

    rows = rows - cen[0]
    cols = cols - cen[1]

    mrr = (rows**2 * psf).sum()
    mcc = (cols**2 * psf).sum()
    mrc = (rows * cols * psf).sum()

    T = mrr + mcc  # noqa
    e1 = (mcc - mrr)/T
    e2 = 2*mrc/T

    assert abs(e1 - shear.e1) < 0.01
    assert abs(e2 - shear.e2) < 0.01


def test_simple_sim_se_shape():
    """
    test we get roughly the right psf shape out. cannot expect detailed
    agreement due to pixelization
    """

    se_dim = 1024
    sim = Sim(rng=10, se_dim=se_dim, gals_kws={'density': 10})
    data = sim.gen_sim()

    for band, bdata in data.items():
        for se_obs in bdata:
            s = se_obs.image.array.shape
            assert s[0] == se_dim and s[1] == se_dim


def test_simple_sim_se_ps_psf():
    sim = Sim(
        rng=10,
        psf_type='ps',
        psf_kws={'noise_level': 0},
        gals_kws={'density': 10},
    )
    data = sim.gen_sim()

    for band, bdata in data.items():
        for se_obs in bdata:
            psf1 = se_obs.get_psf(10, 3)
            psf2 = se_obs.get_psf(500, 100)
            assert not np.allclose(psf1.array, psf2.array)

            if False:
                import matplotlib.pyplot as plt
                fig, axs = plt.subplots(nrows=1, ncols=3, figsize=(12, 4))
                axs[0].imshow(psf1.array)
                axs[1].imshow(psf2.array)
                axs[2].imshow(psf1.array - psf2.array)
                assert False


def test_simple_sim_band_wcs():
    """
    make sure the cacheing code is consistent
    """
    sim = Sim(
        rng=10,
        epochs_per_band=1,
        gals_kws={'density': 10},
    )
    sim.gen_sim()

    for band in sim.bands:
        assert sim._get_wcs_for_band(band) == sim._band_wcs_objs[band]


def test_simple_sim_grid_smoke():
    sim = Sim(
        rng=10,
        layout_type='grid',
        layout_kws={'dim': 10}
    )
    data = sim.gen_sim()

    for band, bdata in data.items():
        for se_obs in bdata:
            if False:
                import matplotlib.pyplot as plt
                fig, axs = plt.subplots(nrows=1, ncols=1, figsize=(8, 8))
                axs.imshow(se_obs.image.array)
                assert False


def test_simple_sim_grid_only_stars_smoke():
    sim = Sim(
        rng=10,
        layout_type='grid',
        layout_kws={'dim': 10},
        gals=False,
        stars=True,
    )
    data = sim.gen_sim()

    for band, bdata in data.items():
        for se_obs in bdata:
            if False:
                import matplotlib.pyplot as plt
                fig, axs = plt.subplots(nrows=1, ncols=1, figsize=(8, 8))
                axs.imshow(se_obs.image.array)
                assert False


def test_simple_sim_grid_stars_and_gals_smoke():

    # on a grid, these are only used to determine the
    # fraction of each type
    star_density = 10
    gal_density = 10
    sim = Sim(
        rng=10,
        layout_type='grid',
        layout_kws={'dim': 10},
        gals=True,
        gals_kws={'density': gal_density},
        stars=True,
        stars_kws={'density': star_density},
        noise_per_band=0,
    )

    # density gets reset
    star_frac = star_density/(star_density + gal_density)
    assert sim.star_density == sim.mean_density*star_frac

    data = sim.gen_sim()

    for band, bdata in data.items():
        for se_obs in bdata:
            if False:
                import matplotlib.pyplot as plt
                fig, axs = plt.subplots(nrows=1, ncols=1, figsize=(8, 8))
                axs.imshow(se_obs.image.array)
                assert False
