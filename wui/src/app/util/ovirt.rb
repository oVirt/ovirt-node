def gb_to_kb(val_in_gigs)
  return nil if val_in_gigs.nil?
  return val_in_gigs.to_i * 1024 * 1024
end
 
def kb_to_gb(val_in_kb)
  return nil if val_in_kb.nil?
  return val_in_kb.to_i / 1024 / 1024
end
def mb_to_kb(val_in_mb)
  return nil if val_in_mb.nil?
  return val_in_mb.to_i * 1024
end
 
def kb_to_mb(val_in_kb)
  return nil if val_in_kb.nil?
  return val_in_kb.to_i / 1024
end
