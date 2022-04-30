import numpy as np
from numpy.lib.arraysetops import unique
import scipy.special as sc
import mpmath as mp
import pandas as pd
from scipy.integrate import quad
from scipy.optimize import dual_annealing, basinhopping
import multiprocessing
import time
import pickle
import csv

dirName = '/Users/saifali/Desktop/gwlensing/SIE_glafic/data/'

class overlap_sie():

    solar_mass = 4.92624076 * 10**-6 #[solar_mass] = sec
    giga_parsec = 1.02927125 * 10**17 #[giga_parsec] = sec
    year = 31557600 #[year] = sec
    


    def __init__(self, params_source = None, params_temp = None):
        
        self.params_source = params_source
        self.params_temp = params_temp

        # Defining source parameters with (t0, phi0)
        self.theta_s_source = params_source['theta_s_source']
        self.phi_s_source = params_source['phi_s_source']
        self.theta_l_source = params_source['theta_l_source']
        self.phi_l_source = params_source['phi_l_source']
        self.mcz_source = params_source['mcz_source']
        self.dist_source = params_source['dist_source']
        self.eta_source = params_source['eta_source']
        self.t0 = params_source['t0']
        self.phi_0 = params_source['phi_0']
        # Adding the lensing params for source
        self.radius = params_source['radius']

        # Defining template parameters 
        self.theta_s_temp = params_temp['theta_s_temp']
        self.phi_s_temp = params_temp['phi_s_temp']
        self.theta_l_temp = params_temp['theta_l_temp']
        self.phi_l_temp = params_temp['phi_l_temp']
        self.mcz_temp = params_temp['mcz_temp']
        self.dist_temp = params_temp['dist_temp']
        self.eta_temp = params_temp['eta_temp']
        #self.tc = params_temp['tc']
        #self.phi_c = params_temp['phi_c']

        # IMPORTING AND SETTING UP DATA FOR AMPLIFICATION FACTOR

        self.DAY = 86400 #[day] = sec
        
        data = dirName + 'flux_twoimages_theta_45_sigma=4_sorted.csv'
        df = pd.read_csv(data)
        df = pd.read_csv(data, float_precision = 'round_trip')
        #np.set_printoptions(precision=3)
        self.radius_data = np.array(df['source_x'])
        self.mu_1_data = np.array(df['mu_1'])
        self.mu_2_data = np.array(df['mu_2'])
        self.td_1_data = np.array(df['td_1'])
        self.td_2_data = np.array(df['td_2'])
        
        

    def limit(self, params_source, params_template):
    
        low_limit = 20
        f_cut_source = 1 / (np.power(6, 3/2) * np.pi * ((self.mcz_source) / (np.power(self.eta_source, 3/5))))
        f_cut_temp = 1 / (np.power(6, 3/2) * np.pi * ((self.mcz_temp) / (np.power(self.eta_temp, 3/5))))

        if f_cut_temp < f_cut_source:
            upper_limit = f_cut_temp

        else:
            upper_limit = f_cut_source
        
        return low_limit, upper_limit, f_cut_source, f_cut_temp

    def strain(self, f, theta_s, phi_s, theta_l, phi_l, mcz, dist, eta, tc, phi_c):
        """
        This file is just functionized form of L_unlensed(which was "object-oriented"). This was mainly created
        for the optimization of overlap function.
        """
        def mass_conv(mcz, eta):
            """Converts chirp mass to total mass. M = mcz/eta^(3/5)
            """

            M_val = mcz/np.power(eta, 3/5)
            return M_val

        def l_dot_n(theta_s, theta_l, phi_s, phi_l):
            """TODO
            """

            cos_term = np.cos(theta_s) * np.cos(theta_l)
            sin_term = np.sin(theta_s) * np.sin(theta_l) * np.cos(phi_s - phi_l)

            inner_prod = cos_term + sin_term
            return inner_prod

        def amp(mcz, dist):
            """TODO
            """

            amplitude = np.sqrt(5 / 96) * np.power(np.pi, -2 / 3) * np.power(mcz, 5 / 6) / (dist)
            return amplitude

        def psi(f, tc, phi_c, mcz, eta):
            """eqn 3.13 in Cutler-Flanaghan 1994
            """

            front_terms = 2 * np.pi * f * tc - phi_c - np.pi / 4
            main_coeffs = 0.75 * np.power(8 * np.pi * mcz * f, -5 / 3)
            main_terms = (1 + 20 / 9 * (743 / 336 + 11 / 4 * eta) * np.power(np.pi * mass_conv(mcz, eta) * f, 2 / 3)
                            - (16 * np.pi) * np.power(np.pi * mass_conv(mcz, eta) * f, 1))

            psi_val = front_terms + main_coeffs * (main_terms)
            return psi_val

        def psi_s(theta_s, theta_l, phi_s, phi_l):

            numerator = np.cos(theta_l)-np.cos(theta_s)*(l_dot_n(theta_s, theta_l, phi_s, phi_l))
            denominator = np.sin(theta_s)*np.sin(theta_l)*np.sin(phi_l-phi_s)

            psi_s_val = np.arctan2(numerator, denominator)
            return psi_s_val


        def fIp(theta_s, phi_s):
            """TODO
            """

            term_1 = (1 / 2 * (1 + np.power(np.cos(theta_s), 2)) * np.cos(2*phi_s)* np.cos(2*psi_s(theta_s, theta_l, phi_s, phi_l)))
            term_2 = (np.cos(theta_s) * np.sin(2*phi_s)* np.sin(2*psi_s(theta_s, theta_l, phi_s, phi_l)))

            fIp_val = term_1 - term_2
            return fIp_val

        def fIc(theta_s, phi_s):
            """TODO
            """

            term_1 = (1 / 2 * (1 + np.power(np.cos(theta_s), 2)) * np.cos(2*phi_s)
                        * np.sin(2*psi_s(theta_s, theta_l, phi_s, phi_l)))
            term_2 = (np.cos(theta_s) * np.sin(2*phi_s)
                        * np.cos(2*psi_s(theta_s, theta_l, phi_s, phi_l)))

            fIc_val = term_1 + term_2
            return fIc_val

        def lambdaI():
            """TODO
            """

            term_1 = np.power(2 * l_dot_n(theta_s, theta_l, phi_s, phi_l) * fIc(theta_s, phi_s), 2)
            term_2 = np.power((1 + np.power(l_dot_n(theta_s, theta_l, phi_s, phi_l), 2)) * fIp(theta_s, phi_s), 2)

            lambdaI_val = np.sqrt(term_1 + term_2)
            return lambdaI_val

        def phi_pI():
            """TODO
            """

            numerator = (2 * l_dot_n(theta_s, theta_l, phi_s, phi_l) * fIc(theta_s, phi_s))
            denominator = ((1 + np.power(l_dot_n(theta_s, theta_l, phi_s, phi_l), 2)) * fIp(theta_s, phi_s))

            phi_pI_val = np.arctan2(numerator, denominator)
            return phi_pI_val

        term_1 = lambdaI()
        term_2 = (np.exp(-1j * phi_pI()))
        term_3 = amp(mcz, dist) * np.power(f, -7 / 6)
        term_4 = np.exp(1j * psi(f, tc, phi_c, mcz, eta))

        signal_I = term_1 * term_2 * term_3 * term_4
        return signal_I

    '''
    Adding in the lens
    '''

    '''
    Amplification factor in geometrical optics limit
    '''

    def F_source_sie(self, f):

        index_radius = np.where(self.radius_data == self.radius)
        mu_1 = self.mu_1_data[index_radius]
        mu_2 = self.mu_2_data[index_radius]
        td_1 = self.td_1_data[index_radius] 
        td_2 = self.td_2_data[index_radius] 
        
        F_source_sie = np.sqrt(np.abs(mu_1)) - 1j * np.sqrt(np.abs(mu_2)) * np.exp(2 * np.pi * 1j * f * td_2)
        
        return F_source_sie[0]

    def Sn(self, f):
        """ ALIGO noise curve from arXiv:0903.0338
        """
        fs = 20
        if f < fs:
            Sn_val = np.inf
        else:
            S0 = 1E-49
            f0 = 215
            Sn_temp = np.power(f/f0, -4.14) - 5 * np.power(f/f0, -2) + 111 * ((1 - np.power(f/f0, 2) + 0.5 * np.power(f/f0, 4)) / (1 + 0.5 * np.power(f/f0, 2)))
            Sn_val = Sn_temp * S0

        return Sn_val

    def signal_source(self, f, t_c, phi_c): # Remove t_c and phi_c for SNR calculation
        
        hI_source = self.strain(
            f, 
            self.theta_s_source,
            self.phi_s_source, 
            self.theta_l_source,
            self.phi_l_source,
            self.mcz_source,
            self.dist_source,
            self.eta_source,
            self.t0,
            self.phi_0
        )
        
        amp_factor_source_sie = self.F_source_sie(f)

        return hI_source * amp_factor_source_sie

    def signal_temp(self, f, t_c, phi_c): 

        hI_temp = self.strain(
            f, 
            self.theta_s_temp,
            self.phi_s_temp, 
            self.theta_l_temp,
            self.phi_l_temp,
            self.mcz_temp,
            self.dist_temp,
            self.eta_temp,
            t_c,
            phi_c
        )

        return hI_temp 

    def integrand_1(self,f, t_c, phi_c):

        integrand_1 = self.signal_source(f, t_c, phi_c) * np.conjugate(self.signal_temp(f, t_c, phi_c)) / self.Sn(f)

        return integrand_1
    
    def integrand_2(self, f, t_c, phi_c):

        integrand_2 = self.signal_source(f, t_c, phi_c) * np.conjugate(self.signal_source(f, t_c, phi_c)) / self.Sn(f)

        return integrand_2

    def integrand_3(self, f, t_c, phi_c):

        integrand_3 = self.signal_temp(f, t_c, phi_c) * np.conjugate(self.signal_temp(f, t_c, phi_c)) / self.Sn(f)

        return integrand_3

    def overlap(self, x):

        t_c = x[0]
        phi_c = x[1]
        
        num_temp, num_err = quad(
            self.integrand_1, 
            self.limit(self.params_source, self.params_temp)[0], 
            self.limit(self.params_source, self.params_temp)[1], 
            args = (t_c, phi_c)
            )

        deno_temp_1, deno_temp_err_1 = quad(
            self.integrand_2,
            self.limit(self.params_source, self.params_temp)[0], 
            self.limit(self.params_source, self.params_temp)[2], 
            args = (t_c, phi_c)
        )
        
        deno_temp_2, deno_temp_err_2 = quad(
            self.integrand_3,
            self.limit(self.params_source, self.params_temp)[0], 
            self.limit(self.params_source, self.params_temp)[3], 
            args = (t_c, phi_c)
        )
        
        num = 4 * np.real(num_temp)
        deno = np.sqrt((4 * np.real(deno_temp_1)) * (4 * np.real(deno_temp_2)))
        overlap_temp = num / deno
        
        return -1 * overlap_temp






solar_mass = 4.92624076 * 10**-6 #[solar_mass] = sec
giga_parsec = 1.02927125 * 10**17 #[giga_parsec] = sec
year = 31557600 #[year] = sec

initial_params_source = {
    'theta_s_source' : 0.0, 
    'phi_s_source' : 0.0, 
    'theta_l_source' : 0.0, 
    'phi_l_source' : 0.0, 
    'mcz_source' : 18.79 * solar_mass, 
    'dist_source': 1.58 * giga_parsec, 
    'eta_source' : 0.25, 
    't0' : 0.0, 
    'phi_0' : 0.0,
    'radius': 0.0
}

initial_params_template = {
    'theta_s_temp' : 0.0, 
    'phi_s_temp' : 0.0, 
    'theta_l_temp' : 0.0, 
    'phi_l_temp' : 0.0, 
    'mcz_temp' : 18.79 * solar_mass, 
    'dist_temp': 1.58 * giga_parsec, 
    'eta_temp' : 0.25, 
    #'tc' : 0.0, 
    #'phi_c' : 0.0,
}

# Custom array generator for uneven spaced lens mass. This is required in order to get more data points at the critical point. 
def my_lin(lb, ub, steps, spacing = 3):

    span = (ub-lb)
    dx = 1.0 / (steps-1)

    return np.array([lb + (i * dx) ** spacing * span for i in range(steps)])


# WITHOUT MULTIPROCESSING
if __name__ == "__main__":
    
    df_res = pd.DataFrame(columns=('source_x', 'overlap', 'tc', 'phi_c'))

    datPath = "/Users/saifali/Desktop/gwlensing/data/"

    data = dirName + 'flux_twoimages_theta_45_sigma=4_sorted.csv'
    df_data = pd.read_csv(data)
    df_data = pd.read_csv(data, float_precision = 'round_trip')
    radius_range = np.array(df_data['source_x'])
    
    start = time.time()
    for i in range(len(radius_range)):

        print(f"working radius is {radius_range[i]}")

        params_source = initial_params_source
        params_template = initial_params_template
        params_source['radius'] = radius_range[i] 
        bnds = [[-0.2, 0.2], [-np.pi, np.pi]]
        overlap_optimized = overlap_sie(params_source = params_source, params_temp = initial_params_template)
        overlap_max = dual_annealing(overlap_optimized.overlap, bounds = bnds, maxiter = 100)
        df_res.loc[i] = [radius_range[i], np.abs(overlap_max.fun), overlap_max.x[0], overlap_max.x[1]]
        end = time.time()
        print(f'elapsed time: {(end - start)/60}')
    print(df_res)
    df_res.to_csv(datPath + "overlap_lensing_sie_theta_45_sigma=4.csv", index = False)
    





# MULTIPROCESSING

'''
def overlap_multiprocessed_lensing(radius_range, return_dict = None):

    bnds = [[-0.2, 0.2], [-np.pi, np.pi]]
    params_source = initial_params_source
    params_source['radius'] = radius_range
    overlap_optimized = overlap_sie(params_source = params_source, params_temp = initial_params_template)
    overlap_max = dual_annealing(overlap_optimized.overlap, bounds = bnds, seed = 42)

    return_dict[radius_range] = [overlap_max.fun, overlap_max.x[0], overlap_max.x[1]]

if __name__ == "__main__":

    datPath = "/Users/saifali/Desktop/gwlensing/data/"
    #start = time.time()
    start = time.strftime("%H%M%S")
    manager = multiprocessing.Manager()
    return_dict = manager.dict()
    processes = []

    radius_range = np.linspace(0.29e-4, 1.98e-4, 10)

    for radius in radius_range:

        process = multiprocessing.Process(target = overlap_multiprocessed_lensing, args=(radius, return_dict))
        processes.append(process)
        process.start()
    
    for proc in processes:
        proc.join()

    w = csv.writer(open(datPath + "overlap_lensing_sie_theta=0.csv", "w"))
    for key, value in return_dict.items():
        w.writerow([key, value])
    
    print(f'start time: {start}')
'''

