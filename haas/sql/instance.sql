CREATE TRIGGER t_instance_audit_stamp_b_iu
       BEFORE INSERT OR UPDATE
    ON ele_instance
   FOR EACH ROW
       EXECUTE PROCEDURE sp_audit_stamps();
