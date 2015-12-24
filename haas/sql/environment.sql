CREATE TRIGGER t_env_audit_stamp_b_iu
       BEFORE INSERT OR UPDATE
    ON ele_environment
   FOR EACH ROW
       EXECUTE PROCEDURE sp_audit_stamps();
