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
    * Password must match three of these rules:
      - Contains as least one or more letter from a-z.
      - Contains as least one or more letter from A-Z.
      - Contains as least one or more digits.
      - Contains as least one or more special characters.

    :param password: Password value check for strength requirements.
    """
    score = 0

    if len(password) < 8:
        return False

    if re.search(re.compile('[A-Z]'), password):
        score += 1

    if re.search(re.compile('[a-z]'), password):
        score += 1

    if re.search(re.compile('\d'), password):
        score += 1

    if re.search(re.compile('[#$%&()*+,-./:;<=>?@\[\]^_{}]'), password):
        score += 1

    return score > 2 and True or False

