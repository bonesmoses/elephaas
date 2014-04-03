import os, random, string, re

def pwgen():
    """
    Generate a "secure" password
    
    This function generates a 10-character string comprised of ascii
    characters. Generated passwords comply with strength guarantees 
    as imposed by the pwcheck function.
    """
    chars = string.ascii_letters + string.digits + '#$%&()*+,-./:;<=>?@[]^_{}'
    random.seed = (os.urandom(1024))

    is_secure = False
    while not is_secure:
        pw = ''.join(random.choice(chars) for i in range(10))
        is_secure = pwcheck(pw)

    return pw

def pwcheck(password):
    """
    Check a password for strength requirements.
    
    This function checks a passed password for the following criteria:

    * Password is at least 8-characters long.
    * Password contains as least one or more letter from a-z.
    * Password contains as least one or more letter from A-Z.
    * Password contains as least one or more digits.
    * Password contains as least one or more special characters.

    :param password: Password value check for strength requirements.
    """
    lc = re.compile('[a-z]')
    uc = re.compile('[A-Z]')
    digits = re.compile('\d')
    special = re.compile('[#$%&()*+,-./:;<=>?@\[\]^_{}]')

    is_secure = False
    if (len(password) > 7 and re.search(uc, password) and
        re.search(lc, password) and re.search(digits, password) and
        re.search(special, password)):

        is_secure = True

    return is_secure
